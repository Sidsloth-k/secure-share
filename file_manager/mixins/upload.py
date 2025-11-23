import base64
import datetime
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from utils import encrypt_file, generate_key
from ..network_utils import (
    NetworkError,
    RetryableError,
    UploadProgress,
    batch_operation_with_rollback,
    retry_with_backoff,
    safe_execute,
)

logger = logging.getLogger("SecureShare")


class UploadMixin:
    """Upload and listing operations for FileManager."""

    def upload_file(self, file_path: str, org_id: str, threshold: int, password: str) -> Optional[Dict]:
        try:
            logger.info(f"Uploading and encrypting file: {file_path}")

            # Get organization members first.
            members = self.org_manager.list_organization_members(org_id)
            if len(members) < threshold:
                raise ValueError(f"Not enough members ({len(members)}) for threshold ({threshold})")

            # Generate encryption key from password and encrypt file.
            key, salt = generate_key(password)
            encrypted_data, nonce = encrypt_file(file_path, key)

            # Generate unique file ID and derive file name.
            file_id = str(uuid.uuid4())
            file_name = os.path.basename(file_path)

            # Create temporary file for upload.
            temp_path = Path("temp") / f"{file_id}.enc"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(encrypted_data)

            # Upload encrypted file to Supabase storage with retry logic.
            # Note: Supabase Storage RLS may not be bypassed by service role key.
            # We use the authenticated user's client which should work with proper storage policies.
            user_id = self.auth.get_user_id()
            if not user_id:
                raise ValueError("User must be authenticated to upload files")

            logger.info(
                f"Uploading to storage using authenticated user client (user_id: {user_id})"
            )

            # Create upload progress tracker
            file_size = temp_path.stat().st_size
            progress = UploadProgress(file_id, str(temp_path), file_size)

            @retry_with_backoff(max_retries=5, initial_delay=2.0)
            def _upload_file():
                """Upload file with retry logic."""
                with open(temp_path, "rb") as f:
                    result = self.client.storage.from_("encrypted-files").upload(
                        path=f"{file_id}/{file_name}",
                        file=f,
                        file_options={
                            "content-type": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                            "x-upsert": "true",
                        },
                    )
                    progress.save_progress(file_size)
                    return result

            try:
                _upload_file()
                progress.clear_progress()
                logger.info(f"Successfully uploaded encrypted file to storage: {file_id}/{file_name}")
            except RetryableError as retry_error:
                error_msg = str(retry_error)
                logger.error(f"Storage upload failed after retries: {retry_error}")
                logger.error("Upload progress saved. You can retry the upload later.")
                raise NetworkError(f"Upload failed due to network issues: {error_msg}") from retry_error
            except Exception as upload_error:
                error_msg = str(upload_error)
                logger.error(f"Storage upload failed: {upload_error}")
                if "row-level security" in error_msg.lower() or "rls" in error_msg.lower():
                    logger.error("=" * 60)
                    logger.error("RLS POLICY VIOLATION - Storage bucket policies need to be configured")
                    logger.error("=" * 60)
                    logger.error("SOLUTION: Configure storage bucket policies in Supabase Dashboard")
                    logger.error("")
                    logger.error("1. Go to: Supabase Dashboard > Storage > encrypted-files > Policies")
                    logger.error("2. Create a policy that allows authenticated organization members to upload")
                    logger.error("3. See docs/STORAGE_RLS_SETUP.md for detailed instructions")
                    logger.error("")
                    logger.error("Policy should allow INSERT for users who are active organization members")
                    logger.error("=" * 60)
                raise
            finally:
                if temp_path.exists():
                    temp_path.unlink()

            # Create file record with additional encryption metadata.
            file_record = {
                "id": file_id,
                "name": file_name,
                "size": len(encrypted_data),
                "type": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                "organization_id": org_id,
                "uploader_id": self.auth.get_user_id(),
                "uploaded_at": datetime.datetime.now().isoformat(),
                "encrypted_at": datetime.datetime.now().isoformat(),
                "storage_path": f"{file_id}/{file_name}",
                "threshold": threshold,
                "total_shares": len(members),
                "nonce": base64.b64encode(nonce).decode(),
                "salt": base64.b64encode(salt).decode(),
                "status": "available",
            }

            self.client.from_("files").insert(file_record).execute()

            # Generate and distribute key shares.
            shares = self.shamir.generate_shares(key, len(members), threshold)
            logger.info(f"Generated {len(shares)} shares with threshold {threshold}")

            # Prepare operations for batch execution with rollback
            share_operations = []
            share_operation_names = []
            rollback_operations = []

            # Insert key share records in the database before distributing.
            # Use an allowed status value (for example, "pending") and a default non-null "cloud_path".
            for i, (share_index, share_data) in enumerate(shares):
                member = members[i]
                share_id = str(uuid.uuid4())
                key_share_record = {
                    "id": share_id,
                    "file_id": file_id,
                    "user_id": member["id"],
                    "share_index": share_index,
                    "status": "pending",  # using an allowed status per your DB constraint
                    "cloud_path": "pending",  # default non-null value to satisfy DB constraint
                }

                # Create operation to insert share record
                def _insert_share(record=key_share_record):
                    self.client.from_("key_shares").insert(record).execute()

                share_operations.append(_insert_share)
                share_operation_names.append(f"Insert share record for {member['display_name']}")

                # Create rollback operation
                def _rollback_share(share_id_to_delete=share_id):
                    try:
                        self.client.from_("key_shares").delete().eq("id", share_id_to_delete).execute()
                    except Exception as e:
                        logger.warning(f"Failed to rollback share {share_id_to_delete}: {e}")

                rollback_operations.append(_rollback_share)

                # Create operation to upload share to cloud
                def _upload_share(m=member, sd=share_data, fid=file_id):
                    member_profile = (
                        self.client.from_("users").select("*").eq("id", m["id"]).single().execute()
                    )
                    if not member_profile.data.get("cloud_connected"):
                        raise ValueError(f"Member {m['display_name']} has no cloud storage connected")

                    cloud_provider = member_profile.data.get("cloud_provider")
                    if cloud_provider == "google_drive":
                        self._upload_to_google_drive(sd, m, fid)
                    elif cloud_provider == "dropbox":
                        self._upload_to_dropbox(sd, m, fid)
                    elif cloud_provider == "onedrive":
                        self._upload_to_onedrive(sd, m, fid)
                    else:
                        raise ValueError(f"Unsupported cloud provider: {cloud_provider}")

                share_operations.append(_upload_share)
                share_operation_names.append(f"Upload share to cloud for {member['display_name']}")

            # Execute all operations with rollback on failure
            success, failed_index = batch_operation_with_rollback(
                share_operations, share_operation_names, rollback_operations
            )

            if not success:
                logger.error(
                    f"Failed to distribute shares. Operation {failed_index} failed. "
                    "Some shares may have been rolled back."
                )
                raise NetworkError(
                    f"Failed to distribute key shares. Operation '{share_operation_names[failed_index]}' failed."
                )

            # Record audit log for successful upload
            self._log_audit(
                org_id,
                file_id,
                "file_uploaded",
                {
                    "file_name": file_name,
                    "size": len(encrypted_data),
                    "threshold": threshold,
                    "total_members": len(members),
                },
            )

            print("File encrypted and shares distributed to cloud storage!")
            verification = self.verify_uploaded_file(file_id)
            print("\nEncryption Verification:")
            print(f"File size: {verification['size']} bytes")
            print(f"Entropy: {verification['entropy']:.2f} bits/byte")
            print(f"Encryption verified: {'Yes' if verification.get('is_encrypted', False) else 'No'}")
            print(f"Shares distributed: {'Yes' if verification.get('shares_distributed', False) else 'No'}")

            return file_record

        except Exception as e:
            logger.error(f"Failed to upload and encrypt file: {e}")
            raise

    def list_files(self, org_id: str) -> List[Dict]:
        """List files in an organization."""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot list files: User not authenticated")
            return []

        @retry_with_backoff(max_retries=3)
        def _list_files():
            logger.info(f"Listing files for organization: {org_id}")
            member_check = (
                self.client.table("organization_members")
                .select("*")
                .eq("organization_id", org_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not member_check.data:
                logger.warning(f"User is not a member of organization: {org_id}")
                return []

            response = (
                self.client.from_("files")
                .select("*, users!uploader_id(display_name)")
                .eq("organization_id", org_id)
                .order("uploaded_at", desc=True)
                .execute()
            )
            files = []
            if response.data:
                for item in response.data:
                    f_rec = {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "size": item.get("size"),
                        "type": item.get("type"),
                        "uploader": item.get("users", {}).get("display_name"),
                        "uploaded_at": item.get("uploaded_at"),
                        "threshold": item.get("threshold"),
                        "total_shares": item.get("total_shares"),
                        "status": item.get("status"),
                        "organization_id": item.get("organization_id"),
                    }
                    files.append(f_rec)
                if getattr(self, "status_tracker", None):
                    files = self.status_tracker.enrich_files(files)
                logger.debug(f"Found {len(files)} files in organization")
            return files

        try:
            files, error = safe_execute(_list_files, "List files", default_return=[])
            if error:
                print("You are not a member of this organization")
            return files if files else []
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []


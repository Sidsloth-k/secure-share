import base64
import datetime
import logging
import shutil
import uuid
from pathlib import Path

from utils import decrypt_file
from ..network_utils import NetworkError, retry_with_backoff, safe_execute

logger = logging.getLogger("SecureShare")


class DecryptionMixin:
    """Decryption workflow for FileManager."""

    def request_decryption(self, file_id: str, reason: str = None) -> bool:
        """Request file decryption."""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot request decryption: User not authenticated")
            raise ValueError("User not authenticated")
        try:
            logger.info(f"Requesting decryption for file: {file_id}")

            @retry_with_backoff(max_retries=3)
            def _get_file():
                return self.client.table("files").select("*").eq("id", file_id).execute()

            file_response, error = safe_execute(_get_file, "Get file", default_return=None)
            if error or not file_response or not file_response.data:
                logger.warning(f"File not found: {file_id}")
                print("File not found")
                return False
            file = file_response.data[0]

            # If a decrypted copy already exists locally, guide the user instead of creating another request
            existing_decryption = self.check_decrypted_file(file_id)
            if existing_decryption.get("status") == "decrypted":
                print(f"\nFile is already decrypted and available at: {existing_decryption['path']}")
                print(f"Decrypted copy expires in: {existing_decryption['expires_in']}")
                input("Press Enter to continue...")
                return False
            elif existing_decryption.get("status") == "decrypted_missing":
                print("\nA decrypted copy was expected but is missing. Creating a new decryption request.")
            elif existing_decryption.get("status") == "expired":
                print("\nPrevious decrypted copy has expired. Creating a new decryption request.")

            org_id = file.get("organization_id")
            threshold = file.get("threshold")

            @retry_with_backoff(max_retries=3)
            def _check_membership():
                return (
                    self.client.table("organization_members")
                    .select("*")
                    .eq("organization_id", org_id)
                    .eq("user_id", user_id)
                    .execute()
                )

            member_check, error = safe_execute(_check_membership, "Check membership", default_return=None)
            if error or not member_check or not member_check.data:
                logger.warning(f"User is not a member of file's organization: {org_id}")
                print("You are not a member of this file's organization")
                return False

            @retry_with_backoff(max_retries=3)
            def _check_existing_request():
                return (
                    self.client.table("decryption_requests")
                    .select("*")
                    .eq("file_id", file_id)
                    .eq("status", "pending")
                    .execute()
                )

            request_check, error = safe_execute(
                _check_existing_request, "Check existing request", default_return=None
            )
            if error or (request_check and request_check.data):
                logger.warning(f"A decryption request is already pending for file: {file_id}")
                print("A decryption request is already pending for this file")
                return False

            expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
            request_data = {
                "id": str(uuid.uuid4()),
                "file_id": file_id,
                "requester_id": user_id,
                "requested_at": datetime.datetime.now().isoformat(),
                "expires_at": expires_at.isoformat(),
                "status": "pending",
                "current_shares": 0,
                "threshold": threshold,
                "message": reason,
            }

            @retry_with_backoff(max_retries=3)
            def _create_request():
                self.client.table("decryption_requests").insert(request_data).execute()

            @retry_with_backoff(max_retries=3)
            def _update_file_status():
                self.client.table("files").update({"status": "pending_decryption"}).eq("id", file_id).execute()

            _create_request()
            logger.debug(f"Decryption request created: {request_data['id']}")
            _update_file_status()

            # Reset key share statuses so members can submit again for the new request
            try:
                (
                    self.client.from_("key_shares")
                    .update({"status": "pending"})
                    .eq("file_id", file_id)
                    .execute()
                )
            except Exception as reset_error:
                logger.warning(f"Failed to reset key share statuses for file {file_id}: {reset_error}")
            # Audit log entry
            self._log_audit(
                org_id,
                file_id,
                "decryption_requested",
                {"reason": reason, "request_id": request_data["id"]},
            )
            print("Decryption request created!")
            print("Request will expire in 24 hours.")
            print(f"Waiting for {threshold} members to submit their key shares...")
            return True
        except Exception as e:
            logger.error(f"Failed to request decryption: {e}")
            print(f"Failed to request decryption: {e}")
            return False

    def submit_key_share(self, request_id: str) -> bool:
        """Submit key share for decryption."""
        try:
            user_id = self.auth.get_user_id()
            if not user_id:
                raise ValueError("User must be authenticated to submit key share")

            @retry_with_backoff(max_retries=3)
            def _get_request():
                return (
                    self.client.from_("decryption_requests")
                    .select("*, files!inner(id, name, organization_id)")
                    .eq("id", request_id)
                    .execute()
                )

            request_resp, error = safe_execute(_get_request, "Get decryption request", raise_on_error=True)
            if error or not request_resp or not request_resp.data:
                raise ValueError("Decryption request not found")
            request_data = request_resp.data[0]

            # Check if request is still pending
            if request_data["status"] != "pending":
                raise ValueError(f"Decryption request is no longer pending (status: {request_data['status']})")

            file_id = request_data["files"]["id"]
            file_org_id = request_data["files"].get("organization_id")
            threshold = request_data["threshold"]

            @retry_with_backoff(max_retries=3)
            def _get_share_record():
                return (
                    self.client.from_("key_shares")
                    .select("*")
                    .eq("file_id", file_id)
                    .eq("user_id", user_id)
                    .execute()
                )

            share_result, error = safe_execute(
                _get_share_record, "Get share record", raise_on_error=True
            )
            if error or not share_result or not share_result.data or len(share_result.data) == 0:
                raise ValueError("You don't have a key share for this file")

            share_record = share_result.data[0]

            # Check if share was already retrieved
            if share_record.get("status") == "retrieved":
                current = request_data.get("current_shares") or 0
                if current >= threshold:
                    raise ValueError("You have already submitted your share for this file")
                logger.info(
                    "Share %s previously submitted for file %s; resetting status to pending before resubmission",
                    share_record["id"],
                    file_id,
                )
                try:
                    (
                        self.client.from_("key_shares")
                        .update({"status": "pending"})
                        .eq("id", share_record["id"])
                        .execute()
                    )
                    share_record["status"] = "pending"
                except Exception as reset_error:
                    logger.warning(f"Failed to reset share status: {reset_error}")
                    raise ValueError("You have already submitted your share for this file")

            @retry_with_backoff(max_retries=3)
            def _get_user():
                return self.client.from_("users").select("*").eq("id", user_id).single().execute()

            user, error = safe_execute(_get_user, "Get user profile", raise_on_error=True)
            if error or not user or not user.data:
                raise ValueError("User profile not found")
            if not user.data.get("cloud_connected"):
                raise ValueError("Cloud storage not connected. Please connect your cloud storage first.")

            @retry_with_backoff(max_retries=5, initial_delay=2.0)
            def _retrieve_share():
                cloud_provider = user.data.get("cloud_provider")
                if cloud_provider == "google_drive":
                    return self._retrieve_from_google_drive(
                        user.data["cloud_credentials"], file_id, share_record["id"]
                    )
                elif cloud_provider == "dropbox":
                    raise NotImplementedError("Dropbox share retrieval not yet implemented")
                elif cloud_provider == "onedrive":
                    raise NotImplementedError("OneDrive share retrieval not yet implemented")
                else:
                    raise ValueError(f"Unsupported cloud provider: {cloud_provider}")

            try:
                share_data = _retrieve_share()
                if not share_data:
                    raise ValueError("Failed to retrieve share from cloud storage")
            except Exception as retrieve_error:
                logger.error(f"Failed to retrieve share after retries: {retrieve_error}")
                raise NetworkError(f"Share retrieval failed: {retrieve_error}") from retrieve_error

            # Cache the share locally
            cache_dir = Path("temp_shares") / request_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            share_path = cache_dir / f"share_{share_record['id']}.bin"
            with open(share_path, "wb") as f:
                f.write(share_data)

            @retry_with_backoff(max_retries=3)
            def _update_share_status():
                self.client.from_("key_shares").update({"status": "retrieved"}).eq(
                    "id", share_record["id"]
                ).execute()

            _update_share_status()

            # Update decryption request with new share count
            current_shares = (request_data.get("current_shares") or 0) + 1
            update_payload = {
                "current_shares": current_shares,
                "status": "pending",
            }
            if current_shares >= threshold:
                update_payload["status"] = "ready"

            @retry_with_backoff(max_retries=3)
            def _update_request():
                self.client.from_("decryption_requests").update(update_payload).eq("id", request_id).execute()

            _update_request()

            self._log_audit(
                file_org_id,
                file_id,
                "key_share_submitted",
                {
                    "request_id": request_id,
                    "current_shares": current_shares,
                    "threshold": threshold,
                    "share_id": share_record["id"],
                },
            )

            if current_shares >= threshold:
                logger.info(f"Threshold reached ({current_shares}/{threshold})! Starting decryption...")
                try:
                    decrypted_path = self._process_decryption(request_id, file_id)
                    # Mark request as completed after successful decryption
                    @retry_with_backoff(max_retries=3)
                    def _mark_completed():
                        self.client.from_("decryption_requests").update({"status": "completed"}).eq(
                            "id", request_id
                        ).execute()

                    _mark_completed()
                    self._log_audit(
                        file_org_id,
                        file_id,
                        "file_decrypted",
                        {"request_id": request_id, "output_path": decrypted_path},
                    )
                    logger.info(f"Decryption completed. File available at {decrypted_path}")
                except Exception:
                    # Revert request status so it can be retried
                    @retry_with_backoff(max_retries=3)
                    def _revert_status():
                        self.client.from_("decryption_requests").update({"status": "pending"}).eq(
                            "id", request_id
                        ).execute()

                    try:
                        _revert_status()
                    except Exception as revert_error:
                        logger.warning(f"Failed to revert request status: {revert_error}")
                    raise
            else:
                logger.info(f"Share submitted! {current_shares}/{threshold} shares collected")

            return True
        except Exception as e:
            logger.exception("Failed to submit key share")
            raise

    def _process_decryption(self, request_id: str, file_id: str) -> str:
        """Process file decryption when threshold is met. Returns decrypted file path."""
        try:
            shares_dir = Path("temp_shares") / request_id
            if not shares_dir.exists():
                raise ValueError("Share cache not found")
            collected_shares = []
            share_files = list(shares_dir.glob("share_*.bin"))
            for share_file in share_files:
                with open(share_file, "rb") as f:
                    share_data = f.read()
                    share_id = share_file.stem.split("_")[1]
                    share_info = (
                        self.client.from_("key_shares")
                        .select("*")
                        .eq("id", share_id)
                        .single()
                        .execute()
                    )
                    # Expecting a field "share_index" in the record.
                    collected_shares.append((share_info.data["share_index"], share_data))

            @retry_with_backoff(max_retries=5, initial_delay=2.0)
            def _get_file():
                return self.client.from_("files").select("*").eq("id", file_id).single().execute()

            @retry_with_backoff(max_retries=5, initial_delay=2.0)
            def _download_encrypted_file(storage_path):
                return self.client.storage.from_("encrypted-files").download(storage_path)

            file = _get_file()
            encrypted_data = _download_encrypted_file(f"{file_id}/{file.data['name']}")
            key = self.shamir.reconstruct_secret(collected_shares)
            decrypted_data = decrypt_file(encrypted_data, key, base64.b64decode(file.data["nonce"]))
            output_dir = Path("temp_decrypted")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / file.data["name"]
            with open(output_path, "wb") as f:
                f.write(decrypted_data)
            expiry_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
            expiry_path = output_dir / f"{file.data['name']}.expiry"
            with open(expiry_path, "w") as f:
                f.write(expiry_time.isoformat())
            self.client.from_("files").update({"status": "decrypted"}).eq("id", file_id).execute()
            shutil.rmtree(shares_dir)
            print(f"File successfully decrypted! Available at: {output_path}")
            print("File will be available for 24 hours")
            self._log_audit(
                file.data["organization_id"],
                file_id,
                "decryption_completed",
                {"request_id": request_id, "output_path": str(output_path)},
            )
            return str(output_path.resolve())
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


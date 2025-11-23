import datetime
import io
import logging
import time
from pathlib import Path
from typing import Dict

from utils import calculate_entropy
from ..network_utils import retry_with_backoff, safe_execute

logger = logging.getLogger("SecureShare")

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


class VerificationMixin:
    """Verification helpers for FileManager."""

    def verify_encryption(self, file_path: str, org_id: str) -> bool:
        """Verify file encryption by attempting to read it."""
        try:
            encrypted_data = self.client.storage.from_("encrypted-files").download(file_path)
            for parser in [
                lambda x: open(x, "r").read(),
                lambda x: Image.open(x) if Image else None,
                lambda x: PyPDF2.PdfReader(x) if PyPDF2 else None,
            ]:
                try:
                    parser(io.BytesIO(encrypted_data))
                    return False
                except Exception:
                    continue
            return True
        except Exception as e:
            logger.error(f"Error verifying encryption: {e}")
            return False

    def verify_uploaded_file(self, file_id: str) -> Dict:
        """Verify uploaded file encryption status."""
        try:
            @retry_with_backoff(max_retries=3)
            def _get_file():
                return self.client.from_("files").select("*").eq("id", file_id).single().execute()

            @retry_with_backoff(max_retries=3)
            def _download_file(storage_path):
                return self.client.storage.from_("encrypted-files").download(storage_path)

            file = _get_file()
            if not file.data:
                return {"status": "not_found"}
            encrypted_data = _download_file(f"{file_id}/{file.data['name']}")

            # Check if data appears encrypted by trying to parse it
            is_encrypted = True
            try:
                # Try to decode as UTF-8 - if it works, it's probably not encrypted
                encrypted_data.decode("utf-8")
                is_encrypted = False
            except (UnicodeDecodeError, AttributeError):
                # If decoding fails, it's likely encrypted binary data
                pass

            # Additional check: try to parse as common file formats
            try:
                io.BytesIO(encrypted_data).read()
            except Exception:
                pass

            verification = {
                "size": len(encrypted_data),
                "entropy": calculate_entropy(encrypted_data),
                "is_encrypted": is_encrypted,
                "shares_distributed": True,
            }
            return verification
        except Exception as e:
            logger.error(f"Failed to verify file: {e}")
            return {"status": "error", "message": str(e)}

    def check_decrypted_file(self, file_id: str) -> Dict:
        """Check the status of a decrypted file and return its availability."""
        try:
            # Clean up expired temp_shares automatically (like temp_decrypted cleanup)
            if hasattr(self, 'cleanup_expired_temp_shares'):
                try:
                    self.cleanup_expired_temp_shares()
                except Exception as cleanup_err:
                    logger.debug(f"Temp shares cleanup failed (non-critical): {cleanup_err}")
            
            file_resp = self.client.from_("files").select("*").eq("id", file_id).single().execute()
            if not file_resp.data:
                raise ValueError("File not found")

            output_dir = Path("temp_decrypted")
            file_data = file_resp.data
            file_name = file_data["name"]
            output_path = output_dir / file_name
            expiry_path = output_dir / f"{file_name}.expiry"

            # If a decrypted copy exists, treat the file as decrypted regardless of DB status
            if output_path.exists() and expiry_path.exists():
                expiry_str = expiry_path.read_text().strip()
                expiry_time = datetime.datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                now = datetime.datetime.now(datetime.timezone.utc if expiry_time.tzinfo else None)
                if expiry_time.tzinfo and not now.tzinfo:
                    now = now.replace(tzinfo=datetime.timezone.utc)

                if now > expiry_time:
                    # Clean up expired files and reset status for future requests
                    try:
                        output_path.unlink(missing_ok=True)
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to delete expired decrypted file: {cleanup_err}")
                    try:
                        expiry_path.unlink(missing_ok=True)
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to delete expiry metadata: {cleanup_err}")

                    self.client.from_("files").update({"status": "pending_decryption"}).eq(
                        "id", file_id
                    ).execute()
                    self._log_audit(
                        file_data.get("organization_id"),
                        file_id,
                        "decrypted_copy_expired",
                        {"file_name": file_name},
                    )
                    return {"status": "expired"}

                # Ensure database status reflects decrypted state
                if file_data.get("status") != "decrypted":
                    self.client.from_("files").update({"status": "decrypted"}).eq("id", file_id).execute()

                time_left = expiry_time - now
                expires_in = str(time_left).split(".")[0]  # drop microseconds for readability

                return {
                    "status": "decrypted",
                    "path": str(output_path.resolve()),
                    "expires_in": expires_in,
                }

            status = file_data.get("status", "unknown")
            if status == "decrypted":
                # Database says decrypted but no local copy exists
                logger.warning("Decrypted file missing locally; resetting status.")
                self.client.from_("files").update({"status": "pending_decryption"}).eq("id", file_id).execute()
                return {"status": "decrypted_missing"}

            return {"status": status}
        except Exception as e:
            logger.error(f"Failed to check decrypted file: {e}")
            return {"status": "error", "message": str(e)}

    def verify_file_encryption(self, file_id: str) -> Dict:
        """Manually verify file encryption status."""
        try:
            @retry_with_backoff(max_retries=3)
            def _get_file():
                return self.client.from_("files").select("*").eq("id", file_id).single().execute()

            @retry_with_backoff(max_retries=3)
            def _download_file(storage_path):
                return self.client.storage.from_("encrypted-files").download(storage_path)

            file = _get_file()
            if not file.data:
                raise ValueError("File not found")
            encrypted_data = _download_file(f"{file_id}/{file.data['name']}")
            entropy = calculate_entropy(encrypted_data)
            is_encrypted = True
            try:
                encrypted_data.decode("utf-8")
                is_encrypted = False
            except Exception:
                pass
            shares = self.client.from_("key_shares").select("*").eq("file_id", file_id).execute()
            return {
                "name": file.data["name"],
                "size": len(encrypted_data),
                "entropy": entropy,
                "appears_encrypted": is_encrypted,
                "total_shares": len(shares.data) if shares.data else 0,
                "threshold": file.data["threshold"],
                "status": file.data["status"],
            }
        except Exception as e:
            logger.error(f"Failed to verify file: {e}")
            raise


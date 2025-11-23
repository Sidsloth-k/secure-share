import datetime
import logging
import shutil
from pathlib import Path

from ..network_utils import retry_with_backoff, safe_execute

logger = logging.getLogger("SecureShare")


class MaintenanceMixin:
    """Maintenance utilities for FileManager."""

    def cleanup_expired_requests(self):
        """Automatically cleanup cached key shares for expired decryption requests."""
        try:
            @retry_with_backoff(max_retries=3)
            def _get_expired_requests():
                now_iso = datetime.datetime.now().isoformat()
                return (
                    self.client.table("decryption_requests")
                    .select("*")
                    .lt("expires_at", now_iso)
                    .eq("status", "pending")
                    .execute()
                )

            expired_requests, error = safe_execute(
                _get_expired_requests, "Get expired requests", default_return=None
            )

            if error or not expired_requests or not expired_requests.data:
                return

            for req in expired_requests.data:
                req_id = req.get("id")
                try:
                    # Remove cached share files if they exist.
                    shares_dir = Path("temp_shares") / req_id
                    if shares_dir.exists():
                        shutil.rmtree(shares_dir)
                        logger.info(
                            f"Removed temporary share directory for expired request {req_id}"
                        )

                    # Optionally mark the request as expired.
                    @retry_with_backoff(max_retries=3)
                    def _mark_expired():
                        self.client.table("decryption_requests").update({"status": "expired"}).eq(
                            "id", req_id
                        ).execute()

                    _mark_expired()
                    logger.info(f"Decryption request {req_id} marked as expired")
                except Exception as req_error:
                    logger.warning(f"Failed to cleanup request {req_id}: {req_error}")
                    continue
        except Exception as e:
            logger.error(f"Cleanup expired requests failed: {e}")


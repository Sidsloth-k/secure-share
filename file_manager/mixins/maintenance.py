import datetime
import logging
import shutil
from pathlib import Path

from ..network_utils import retry_with_backoff, safe_execute

logger = logging.getLogger("SecureShare")


class MaintenanceMixin:
    """Maintenance utilities for FileManager."""

    def cleanup_expired_temp_shares(self):
        """Automatically cleanup expired temporary share directories based on expiry metadata or file age."""
        try:
            temp_shares_dir = Path("temp_shares")
            if not temp_shares_dir.exists():
                return

            now = datetime.datetime.now(datetime.timezone.utc)
            cleaned_count = 0
            
            # Check each request directory in temp_shares
            for request_dir in temp_shares_dir.iterdir():
                if not request_dir.is_dir():
                    continue
                
                try:
                    expiry_path = request_dir / ".expiry"
                    should_cleanup = False
                    
                    # Check expiry metadata if it exists
                    if expiry_path.exists():
                        try:
                            expiry_str = expiry_path.read_text().strip()
                            expiry_time = datetime.datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                            if expiry_time.tzinfo and not now.tzinfo:
                                now = now.replace(tzinfo=datetime.timezone.utc)
                            
                            if now > expiry_time:
                                should_cleanup = True
                                logger.debug(f"Share directory {request_dir.name} expired at {expiry_time}")
                        except (ValueError, OSError) as expiry_err:
                            logger.warning(f"Failed to read expiry metadata for {request_dir.name}: {expiry_err}")
                            # Fall through to age-based cleanup
                    
                    # Fallback: Check directory age (72 hours default)
                    if not should_cleanup:
                        try:
                            dir_mtime = datetime.datetime.fromtimestamp(
                                request_dir.stat().st_mtime, tz=datetime.timezone.utc
                            )
                            age = now - dir_mtime
                            # Clean up if older than 72 hours (REQUEST_TIMEOUT)
                            if age > datetime.timedelta(hours=72):
                                should_cleanup = True
                                logger.debug(f"Share directory {request_dir.name} is {age} old, cleaning up")
                        except OSError as stat_err:
                            logger.warning(f"Failed to get directory stats for {request_dir.name}: {stat_err}")
                            continue
                    
                    if should_cleanup:
                        shutil.rmtree(request_dir)
                        cleaned_count += 1
                        logger.info(f"Cleaned up expired temporary share directory: {request_dir.name}")
                        
                except Exception as dir_error:
                    logger.warning(f"Failed to process share directory {request_dir.name}: {dir_error}")
                    continue
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired temporary share directory(ies)")
            
        except Exception as e:
            logger.error(f"Cleanup expired temp shares failed: {e}")

    def cleanup_expired_requests(self):
        """Automatically cleanup cached key shares for expired decryption requests."""
        try:
            # Also cleanup expired temp_shares based on expiry metadata/age
            self.cleanup_expired_temp_shares()
            
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


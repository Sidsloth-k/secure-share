import datetime
import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("SecureShare")


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        else:
            parsed = parsed.astimezone(datetime.timezone.utc)
        return parsed
    except Exception:
        return None


def _format_timedelta(delta: Optional[datetime.timedelta]) -> str:
    if not delta:
        return "N/A"
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class FileStatusTracker:
    """Encapsulates file status normalization, timers, and automatic cleanup."""

    REQUEST_TIMEOUT = datetime.timedelta(hours=72)

    def __init__(
        self,
        client,
        audit_logger: Callable[[Optional[str], Optional[str], str, Optional[dict]], None],
        decrypted_checker: Callable[[str], Dict],
    ):
        self.client = client
        self._log_audit = audit_logger
        self._check_decrypted = decrypted_checker

    def enrich_files(self, files: List[Dict]) -> List[Dict]:
        if not files:
            return []

        file_ids = [f["id"] for f in files if f.get("id")]
        request_map = self._fetch_active_requests(file_ids)
        now = datetime.datetime.now(datetime.timezone.utc)

        for file_record in files:
            try:
                self._normalize_record(file_record, request_map.get(file_record["id"]), now)
            except Exception as err:
                logger.warning(f"Failed to normalize file {file_record.get('id')}: {err}")
        return files

    def _normalize_record(self, file_record: Dict, request: Optional[Dict], now: datetime.datetime) -> None:
        status = file_record.get("status", "unknown")

        if status == "expired":
            self._restore_available(file_record, reason="expired_cleanup")
            status = "available"

        if status == "pending_decryption":
            self._handle_pending_decryption(file_record, request, now)
        elif status == "decrypted":
            self._handle_decrypted_record(file_record)
        elif status not in {"available", "pending_decryption", "decrypted"}:
            # Unknown statuses should not block usage; normalize to available
            self._restore_available(file_record, reason="unknown_status")

    def _handle_pending_decryption(self, file_record: Dict, request: Optional[Dict], now: datetime.datetime) -> None:
        if not request:
            logger.info(
                "File %s marked pending_decryption but no active request found; resetting",
                file_record.get("id"),
            )
            self._restore_available(file_record, reason="missing_request")
            return

        expires_at = _parse_iso_datetime(request.get("expires_at"))
        requested_at = _parse_iso_datetime(request.get("requested_at"))
        current_shares = request.get("current_shares") or 0
        threshold = request.get("threshold") or file_record.get("threshold")

        if expires_at and now > expires_at:
            self._expire_request(file_record, request, "request_window_elapsed")
            return

        if (
            current_shares == 0
            and requested_at
            and now - requested_at >= self.REQUEST_TIMEOUT
        ):
            self._expire_request(file_record, request, "no_shares_within_72h")
            return

        time_remaining = expires_at - now if expires_at else None
        file_record["decryption_info"] = {
            "request_id": request.get("id"),
            "current_shares": current_shares,
            "threshold": threshold,
            "expires_in": _format_timedelta(time_remaining),
            "expires_at": request.get("expires_at"),
        }

    def _handle_decrypted_record(self, file_record: Dict) -> None:
        file_id = file_record.get("id")
        if not file_id:
            return
        status_info = self._check_decrypted(file_id)
        status = status_info.get("status")
        if status == "decrypted":
            file_record["decrypted_expires_in"] = status_info.get("expires_in")
        else:
            # check_decrypted_file already normalized DB state; mirror result locally
            file_record["status"] = status
            file_record.pop("decrypted_expires_in", None)

    def _restore_available(self, file_record: Dict, reason: str) -> None:
        file_id = file_record.get("id")
        if not file_id:
            return
        try:
            self.client.from_("files").update({"status": "available"}).eq("id", file_id).execute()
            file_record["status"] = "available"
            file_record.pop("decryption_info", None)
            self._log_audit(
                file_record.get("organization_id"),
                file_id,
                "file_status_reset",
                {"reason": reason},
            )
        except Exception as err:
            logger.warning(f"Failed to restore file {file_id} to available: {err}")

    def _expire_request(self, file_record: Dict, request: Dict, reason: str) -> None:
        request_id = request.get("id")
        file_id = file_record.get("id")
        try:
            if request_id:
                self.client.table("decryption_requests").update({"status": "expired"}).eq(
                    "id", request_id
                ).execute()
        except Exception as err:
            logger.warning(f"Failed to mark request {request_id} as expired: {err}")

        self._restore_available(file_record, reason=reason)
        self._log_audit(
            file_record.get("organization_id"),
            file_id,
            "decryption_request_expired",
            {"request_id": request_id, "reason": reason},
        )

    def _fetch_active_requests(self, file_ids: List[str]) -> Dict[str, Dict]:
        if not file_ids:
            return {}
        try:
            response = (
                self.client.table("decryption_requests")
                .select("*")
                .in_("file_id", file_ids)
                .in_("status", ["pending", "ready"])
                .execute()
            )
            if not response.data:
                return {}
            return {item["file_id"]: item for item in response.data if item.get("file_id")}
        except Exception as err:
            logger.warning(f"Failed to fetch active decryption requests: {err}")
            return {}



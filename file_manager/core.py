import logging
from typing import Optional

from .cloud_storage import CloudStorageMixin
from .mixins import (
    DecryptionMixin,
    MaintenanceMixin,
    UploadMixin,
    VerificationMixin,
)
from .shamir import ShamirSecretSharing
from .status_tracker import FileStatusTracker

logger = logging.getLogger("SecureShare")

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

class FileManager(
    CloudStorageMixin,
    UploadMixin,
    DecryptionMixin,
    VerificationMixin,
    MaintenanceMixin,
):
    """Handles file encryption, storage, and management."""

    def __init__(self, client, auth, org_manager, storage_client=None):
        self.client = client
        self.storage_client = storage_client or client
        self.auth = auth
        self.org_manager = org_manager
        self.shamir = ShamirSecretSharing()
        self.status_tracker = FileStatusTracker(
            self.client,
            self._log_audit,
            self.check_decrypted_file,
        )
        # Log which client is being used for storage
        if storage_client and storage_client != client:
            logger.info(
                "FileManager using service role client for storage operations (bypasses RLS)"
            )
        else:
            logger.warning(
                "FileManager using regular client for storage operations - RLS may block uploads"
            )
        logger.debug("File manager initialized")

    def _log_audit(
        self, org_id: Optional[str], file_id: Optional[str], action: str, details: Optional[dict] = None
    ) -> None:
        """Safely create an audit log entry."""
        if not org_id or not getattr(self, "org_manager", None):
            return
        try:
            self.org_manager._create_audit_log(org_id, file_id, action, details or {})
        except Exception as audit_error:
            logger.warning(f"Failed to record audit log '{action}': {audit_error}")

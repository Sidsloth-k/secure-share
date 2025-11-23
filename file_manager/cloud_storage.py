import datetime
import io
import logging
import os
import zipfile
from typing import Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow

from .network_utils import NetworkError, retry_with_backoff, safe_execute

logger = logging.getLogger("SecureShare")


class CloudStorageMixin:
    """Cloud storage helper methods for FileManager."""

    def _upload_to_google_drive(self, share_data: bytes, member: Dict, file_id: str):
        """Uploads a zipped share file to the member's Google Drive.
           If token refresh fails, force reauthentication."""
        try:
            member_profile = (
                self.client.from_("users").select("*").eq("id", member["id"]).single().execute()
            )
            if not member_profile.data:
                raise ValueError(f"No profile found for member: {member['display_name']}")

            cloud_creds = member_profile.data.get("cloud_credentials", {})
            required_fields = [
                "token",
                "refresh_token",
                "token_uri",
                "client_id",
                "client_secret",
                "scopes",
            ]
            missing_fields = [field for field in required_fields if not cloud_creds.get(field)]
            if missing_fields:
                logger.warning(
                    f"Incomplete credentials for {member['display_name']}, initiating reconnection"
                )
                cloud_creds = self._reauthenticate_google_drive(member)

            credentials = Credentials(
                token=cloud_creds["token"],
                refresh_token=cloud_creds["refresh_token"],
                token_uri=cloud_creds["token_uri"],
                client_id=cloud_creds["client_id"],
                client_secret=cloud_creds["client_secret"],
                scopes=cloud_creds["scopes"],
            )
            if not credentials.valid or credentials.expired:
                try:
                    credentials.refresh(Request())
                    cloud_creds.update(
                        {
                            "token": credentials.token,
                            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                        }
                    )
                    self.client.from_("users").update(
                        {
                            "cloud_credentials": cloud_creds,
                            "updated_at": datetime.datetime.now().isoformat(),
                        }
                    ).eq("id", member["id"]).execute()
                    logger.info("Credentials refreshed successfully")
                except Exception as refresh_error:
                    logger.error(f"Credentials refresh failed: {refresh_error}")
                    cloud_creds = self._reauthenticate_google_drive(member)
                    credentials = Credentials(
                        token=cloud_creds["token"],
                        refresh_token=cloud_creds["refresh_token"],
                        token_uri=cloud_creds["token_uri"],
                        client_id=cloud_creds["client_id"],
                        client_secret=cloud_creds["client_secret"],
                        scopes=cloud_creds["scopes"],
                    )

            service = build("drive", "v3", credentials=credentials)

            @retry_with_backoff(max_retries=5, initial_delay=2.0)
            def _get_or_create_folder():
                """Get or create the SecureShare folder with retry."""
                folder_name = "SecureShare_KeyShares"
                folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
                folder_results = service.files().list(q=folder_query, spaces="drive").execute()
                if not folder_results.get("files"):
                    folder_metadata = {
                        "name": folder_name,
                        "mimeType": "application/vnd.google-apps.folder",
                    }
                    folder = service.files().create(body=folder_metadata, fields="id").execute()
                    return folder["id"]
                else:
                    return folder_results["files"][0]["id"]

            folder_id, error = safe_execute(
                _get_or_create_folder,
                "Get or create Google Drive folder",
                raise_on_error=True,
            )
            if error:
                raise NetworkError(f"Failed to get or create folder: {error}") from error

            # Zip the share before upload.
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(f"share_{file_id}.bin", share_data)
            zip_buffer.seek(0)

            @retry_with_backoff(max_retries=5, initial_delay=2.0)
            def _upload_to_drive():
                """Upload file to Google Drive with retry."""
                file_metadata = {
                    "name": f"share_{file_id}.zip",
                    "parents": [folder_id],
                }
                media = MediaIoBaseUpload(zip_buffer, mimetype="application/zip", resumable=True)
                return service.files().create(body=file_metadata, media_body=media, fields="id").execute()

            try:
                _upload_to_drive()
                logger.info(
                    f"Successfully uploaded zipped share to Google Drive for member: {member['display_name']}"
                )
            except Exception as upload_error:
                logger.error(f"Failed to upload share to Google Drive after retries: {upload_error}")
                raise NetworkError(f"Google Drive upload failed: {upload_error}") from upload_error

        except Exception as e:
            logger.error(f"Failed to upload to Google Drive: {e}")
            raise

    def _reauthenticate_google_drive(self, member: Dict) -> Dict:
        """Force reauthenticate the user for Google Drive and update the credentials."""
        try:
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            if not client_id or not client_secret:
                raise ValueError("Google Drive API credentials not found in environment")

            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uris": ["http://localhost:8080"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=["https://www.googleapis.com/auth/drive.file"],
                prompt="consent",
            )
            print(f"\nReauthenticating Google Drive for {member['display_name']}...")
            credentials = flow.run_local_server(
                host="localhost", port=8080, access_type="offline", include_granted_scopes="true"
            )
            cloud_creds = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": credentials.scopes,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            }
            self.client.from_("users").update(
                {
                    "cloud_credentials": cloud_creds,
                    "cloud_connected": True,
                    "updated_at": datetime.datetime.now().isoformat(),
                }
            ).eq("id", member["id"]).execute()
            logger.info(f"Reauthentication successful for {member['display_name']}")
            return cloud_creds
        except Exception as e:
            logger.error(f"Reauthentication failed for {member['display_name']}: {e}")
            raise

    def _retrieve_from_google_drive(self, cloud_creds: dict, file_id: str, share_id: str) -> bytes:
        """Retrieve zipped share from Google Drive, unzip it, and return the share binary."""
        credentials = Credentials(
            token=cloud_creds["token"],
            refresh_token=cloud_creds["refresh_token"],
            token_uri=cloud_creds["token_uri"],
            client_id=cloud_creds["client_id"],
            client_secret=cloud_creds["client_secret"],
            scopes=cloud_creds["scopes"],
        )
        service = build("drive", "v3", credentials=credentials)

        @retry_with_backoff(max_retries=5, initial_delay=2.0)
        def _find_folder():
            """Find the SecureShare folder with retry."""
            folder_name = "SecureShare_KeyShares"
            folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            folder_results = service.files().list(q=folder_query, spaces="drive").execute()
            if not folder_results.get("files"):
                raise ValueError("Key share folder not found on Google Drive.")
            return folder_results["files"][0]["id"]

        @retry_with_backoff(max_retries=5, initial_delay=2.0)
        def _find_file(folder_id):
            """Find the share file with retry."""
            query = f"'{folder_id}' in parents and name='share_{file_id}.zip'"
            results = service.files().list(q=query, spaces="drive").execute()
            items = results.get("files", [])
            if not items:
                raise ValueError("Share file not found in Google Drive.")
            return items[0]["id"]

        @retry_with_backoff(max_retries=5, initial_delay=2.0)
        def _download_file(drive_file_id):
            """Download file from Google Drive with retry."""
            request = service.files().get_media(fileId=drive_file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)
            with zipfile.ZipFile(fh, "r") as zipf:
                names = zipf.namelist()
                if not names:
                    raise ValueError("Zip share file is empty.")
                return zipf.read(names[0])

        try:
            folder_id = _find_folder()
            drive_file_id = _find_file(folder_id)
            share_data = _download_file(drive_file_id)
            return share_data
        except Exception as e:
            logger.error(f"Failed to retrieve share from Google Drive after retries: {e}")
            raise NetworkError(f"Google Drive retrieval failed: {e}") from e

    def _upload_to_dropbox(self, share_data: bytes, member: Dict, file_id: str):
        """Placeholder for Dropbox share upload (implement similar to Google Drive)"""
        logger.info("Dropbox upload not yet implemented.")
        raise NotImplementedError("Dropbox integration is not implemented yet.")

    def _upload_to_onedrive(self, share_data: bytes, member: Dict, file_id: str):
        """Placeholder for OneDrive share upload (implement similar to Google Drive)"""
        logger.info("OneDrive upload not yet implemented.")
        raise NotImplementedError("OneDrive integration is not implemented yet.")


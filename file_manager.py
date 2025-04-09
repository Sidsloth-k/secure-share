import os
import sys
import uuid
import json
import time
import datetime
import base64
import mimetypes
import logging
import shutil
import secrets
import io
import math
import zipfile
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional


# Import helper functions from your utils module.
from utils import generate_key, encrypt_file, decrypt_file, calculate_entropy

# Import external modules required for Google Drive operations.
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request

# If you use image or PDF parsing for encryption verification, import them:
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# Set up logging
logger = logging.getLogger("SecureShare")
logger.setLevel(logging.DEBUG)

TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'


class ShamirSecretSharing:
    """A simple Shamir's secret sharing scheme implementation."""
    
    def __init__(self, prime: int = 2**256 - 189):
        self.prime = prime
        logger.debug(f"Initialized Shamir's Secret Sharing with prime: {prime}")
    
    def _mod_inverse(self, x: int, p: int) -> int:
        return pow(x, p - 2, p)
    
    def _eval_polynomial(self, coeffs: List[int], x: int) -> int:
        result = 0
        for coeff in reversed(coeffs):
            result = (result * x + coeff) % self.prime
        return result
    
    def generate_shares(self, secret: bytes, n: int, t: int) -> List[tuple]:
        if t > n:
            raise ValueError("Threshold cannot be greater than number of shares")
        logger.info(f"Generating {n} shares with threshold {t}")
        secret_int = int.from_bytes(secret, byteorder='big')
        coeffs = [secret_int] + [secrets.randbelow(self.prime) for _ in range(t - 1)]
        shares = []
        for i in range(1, n + 1):
            x = i
            y = self._eval_polynomial(coeffs, x)
            # Store y in a fixed 32-byte length representation.
            y_bytes = y.to_bytes(32, byteorder='big')
            shares.append((x, y_bytes))
        logger.debug(f"Generated {len(shares)} shares")
        return shares
    
    def reconstruct_secret(self, shares: List[tuple], key_length: int = 32) -> bytes:
        if not shares:
            raise ValueError("No shares provided")
        result = 0
        for i, (x_i, y_i_bytes) in enumerate(shares):
            y_i = int.from_bytes(y_i_bytes, byteorder='big')
            numerator, denominator = 1, 1
            for j, (x_j, _) in enumerate(shares):
                if i == j:
                    continue
                numerator = (numerator * (-x_j)) % self.prime
                denominator = (denominator * (x_i - x_j)) % self.prime
            lagrange = y_i * numerator * self._mod_inverse(denominator, self.prime)
            result = (result + lagrange) % self.prime
        return result.to_bytes(key_length, byteorder='big')


class FileManager:
    """Handles file encryption, storage, and management."""
    
    def __init__(self, client, auth, org_manager):
        self.client = client
        self.auth = auth
        self.org_manager = org_manager
        self.shamir = ShamirSecretSharing()
        logger.debug("File manager initialized")
    
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
            with open(temp_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Upload encrypted file to storage.
            try:
                with open(temp_path, 'rb') as f:
                    self.client.storage.from_('encrypted-files').upload(
                        path=f"{file_id}/{file_name}",
                        file=f,
                        file_options={
                            "content-type": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                            "x-upsert": "true"
                        }
                    )
                logger.debug("Encrypted file uploaded to cloud storage")
            except Exception as upload_error:
                logger.error(f"Storage upload failed: {upload_error}")
                raise
            finally:
                if temp_path.exists():
                    temp_path.unlink()
            
            # Create file record with additional encryption metadata.
            file_record = {
                'id': file_id,
                'name': file_name,
                'size': len(encrypted_data),
                'type': mimetypes.guess_type(file_path)[0] or 'application/octet-stream',
                'organization_id': org_id,
                'uploader_id': self.auth.get_user_id(),
                'uploaded_at': datetime.datetime.now().isoformat(),
                'encrypted_at': datetime.datetime.now().isoformat(),
                'storage_path': f"{file_id}/{file_name}",
                'threshold': threshold,
                'total_shares': len(members),
                'nonce': base64.b64encode(nonce).decode(),
                'salt': base64.b64encode(salt).decode(),
                'status': 'available'
            }
            
            self.client.from_('files').insert(file_record).execute()
            logger.debug(f"File record created for file_id: {file_id}")
            
            # Generate and distribute key shares.
            shares = self.shamir.generate_shares(key, len(members), threshold)
            logger.info(f"Generated {len(shares)} shares with threshold {threshold}")

            # For each member, create a key share record and upload the share file uniquely.
            for i, (share_index, share_data) in enumerate(shares):
                member = members[i]
                key_share_id = str(uuid.uuid4())
                # Create a key share record with a placeholder for cloud_path.
                key_share_record = {
                    "id": key_share_id,
                    "file_id": file_id,
                    "user_id": member['id'],
                    "share_index": share_index,
                    "status": "created",
                    "cloud_path": ""  # will update after upload
                }
                self.client.from_('key_shares').insert(key_share_record).execute()
                logger.debug(f"Created key share record with id: {key_share_id} for user: {member['id']}")

                # Now distribute the share to the member's cloud storage.
                cloud_provider = None
                member_profile = self.client.from_('users').select('*').eq('id', member['id']).single().execute()
                if not member_profile.data.get('cloud_connected'):
                    raise ValueError(f"Member {member['display_name']} has no cloud storage connected")
                cloud_provider = member_profile.data.get('cloud_provider')
                if cloud_provider == 'google_drive':
                    # Pass the key share record id to update the cloud_path later.
                    self._upload_to_google_drive(share_data, member, file_id, key_share_id)
                elif cloud_provider == 'dropbox':
                    self._upload_to_dropbox(share_data, member, file_id, key_share_id)
                elif cloud_provider == 'onedrive':
                    self._upload_to_onedrive(share_data, member, file_id, key_share_id)
                else:
                    logger.warning(f"Cloud provider {cloud_provider} not supported for member {member['display_name']}")
            
            print("File encrypted and key shares distributed to cloud storage!")
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

    def _upload_to_google_drive(self, share_data: bytes, member: Dict, file_id: str, key_share_id: str):
        """
        Uploads a zipped share file to the member's Google Drive with a unique name,
        then updates the key share record with the cloud path.
        """
        try:
            member_profile = self.client.from_('users').select('*').eq('id', member['id']).single().execute()
            if not member_profile.data:
                raise ValueError(f"No profile found for member: {member['display_name']}")
            
            cloud_creds = member_profile.data.get('cloud_credentials', {})
            required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret', 'scopes']
            missing_fields = [field for field in required_fields if not cloud_creds.get(field)]
            if missing_fields:
                logger.warning(f"Incomplete credentials for {member['display_name']}, initiating reconnection")
                cloud_creds = self._reauthenticate_google_drive(member)
            
            credentials = Credentials(
                token=cloud_creds['token'],
                refresh_token=cloud_creds['refresh_token'],
                token_uri=cloud_creds['token_uri'],
                client_id=cloud_creds['client_id'],
                client_secret=cloud_creds['client_secret'],
                scopes=cloud_creds['scopes']
            )
            if not credentials.valid or credentials.expired:
                try:
                    credentials.refresh(Request())
                    cloud_creds.update({
                        'token': credentials.token,
                        'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                    })
                    self.client.from_('users').update({
                        'cloud_credentials': cloud_creds,
                        'updated_at': datetime.datetime.now().isoformat()
                    }).eq('id', member['id']).execute()
                    logger.info("Credentials refreshed successfully")
                except Exception as refresh_error:
                    logger.error(f"Credentials refresh failed: {refresh_error}")
                    cloud_creds = self._reauthenticate_google_drive(member)
                    credentials = Credentials(
                        token=cloud_creds['token'],
                        refresh_token=cloud_creds['refresh_token'],
                        token_uri=cloud_creds['token_uri'],
                        client_id=cloud_creds['client_id'],
                        client_secret=cloud_creds['client_secret'],
                        scopes=cloud_creds['scopes']
                    )
            
            service = build('drive', 'v3', credentials=credentials)
            
            folder_name = 'SecureShare_KeyShares'
            folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            folder_results = service.files().list(q=folder_query, spaces='drive').execute()
            if not folder_results.get('files'):
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder['id']
            else:
                folder_id = folder_results['files'][0]['id']
            logger.debug(f"Google Drive folder id: {folder_id}")
            
            # Create a unique file name for this key share
            unique_share_filename = f"share_{file_id}_{member['id']}.zip"
            
            # Zip the share before upload.
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(unique_share_filename.replace(".zip", ".bin"), share_data)
            zip_buffer.seek(0)
            
            file_metadata = {
                'name': unique_share_filename,
                'parents': [folder_id]
            }
            media = MediaIoBaseUpload(zip_buffer, mimetype='application/zip', resumable=True)
            upload_response = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            logger.info(f"Successfully uploaded zipped share to Google Drive for member: {member['display_name']}")
            logger.debug(f"Google Drive upload response: {upload_response}")
            
            # Update the key share record with the actual cloud file name.
            update_data = {'cloud_path': unique_share_filename, 'status': 'uploaded'}
            self.client.from_('key_shares').update(update_data).eq('id', key_share_id).execute()
            logger.debug(f"Key share record {key_share_id} updated with cloud_path: {unique_share_filename}")
            
        except Exception as e:
            logger.error(f"Failed to upload to Google Drive: {e}")
            raise

    def _reauthenticate_google_drive(self, member: Dict) -> Dict:
        """Force reauthenticate the user for Google Drive and update the credentials."""
        try:
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
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
                scopes=['https://www.googleapis.com/auth/drive.file'],
                prompt='consent'
            )
            print(f"\nReauthenticating Google Drive for {member['display_name']}...")
            credentials = flow.run_local_server(
                host='localhost',
                port=8080,
                access_type='offline',
                include_granted_scopes='true'
            )
            cloud_creds = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': client_id,
                'client_secret': client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            self.client.from_('users').update({
                'cloud_credentials': cloud_creds,
                'cloud_connected': True,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', member['id']).execute()
            logger.info(f"Reauthentication successful for {member['display_name']}")
            return cloud_creds
        except Exception as e:
            logger.error(f"Reauthentication failed for {member['display_name']}: {e}")
            raise

    def _upload_to_dropbox(self, share_data: bytes, member: Dict, file_id: str, key_share_id: str):
        """Placeholder for Dropbox share upload (implement similar to Google Drive)."""
        logger.info("Dropbox upload not yet implemented.")
        raise NotImplementedError("Dropbox integration is not implemented yet.")

    def _upload_to_onedrive(self, share_data: bytes, member: Dict, file_id: str, key_share_id: str):
        """Placeholder for OneDrive share upload (implement similar to Google Drive)."""
        logger.info("OneDrive upload not yet implemented.")
        raise NotImplementedError("OneDrive integration is not implemented yet.")

    def list_files(self, org_id: str) -> List[Dict]:
        """List files in an organization."""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot list files: User not authenticated")
            return []
        try:
            logger.info(f"Listing files for organization: {org_id}")
            member_check = self.client.table('organization_members').select('*')\
                .eq('organization_id', org_id)\
                .eq('user_id', user_id)\
                .execute()
            if not member_check.data:
                logger.warning(f"User is not a member of organization: {org_id}")
                print("You are not a member of this organization")
                return []
            response = self.client.from_('files').select('*, users!uploader_id(display_name)')\
                .eq('organization_id', org_id)\
                .order('uploaded_at', desc=True)\
                .execute()
            files = []
            if response.data:
                for item in response.data:
                    f_rec = {
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'size': item.get('size'),
                        'type': item.get('type'),
                        'uploader': item.get('users', {}).get('display_name'),
                        'uploaded_at': item.get('uploaded_at'),
                        'threshold': item.get('threshold'),
                        'total_shares': item.get('total_shares'),
                        'status': item.get('status')
                    }
                    files.append(f_rec)
                logger.debug(f"Found {len(files)} files in organization")
            return files
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def request_decryption(self, file_id: str, reason: str = None) -> bool:
        """Request file decryption."""
        user_id = self.auth.get_user_id()
        if not user_id:
            logger.warning("Cannot request decryption: User not authenticated")
            raise ValueError("User not authenticated")
        try:
            logger.info(f"Requesting decryption for file: {file_id}")
            file_response = self.client.table('files').select('*').eq('id', file_id).execute()
            if not file_response.data:
                logger.warning(f"File not found: {file_id}")
                print("File not found")
                return False
            file = file_response.data[0]
            org_id = file.get('organization_id')
            threshold = file.get('threshold')
            member_check = self.client.table('organization_members').select('*')\
                .eq('organization_id', org_id)\
                .eq('user_id', user_id)\
                .execute()
            if not member_check.data:
                logger.warning(f"User is not a member of file's organization: {org_id}")
                print("You are not a member of this file's organization")
                return False
            request_check = self.client.table('decryption_requests').select('*')\
                .eq('file_id', file_id)\
                .eq('status', 'pending')\
                .execute()
            if request_check.data:
                logger.warning(f"A decryption request is already pending for file: {file_id}")
                print("A decryption request is already pending for this file")
                return False
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
            request_data = {
                'id': str(uuid.uuid4()),
                'file_id': file_id,
                'requester_id': user_id,
                'requested_at': datetime.datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'status': 'pending',
                'current_shares': 0,
                'threshold': threshold,
                'message': reason
            }
            self.client.table('decryption_requests').insert(request_data).execute()
            logger.debug(f"Decryption request created for file_id: {file_id}")
            self.client.table('files').update({'status': 'pending_decryption'})\
                .eq('id', file_id).execute()
            self.org_manager._create_audit_log(org_id, file_id, 'decryption_requested', {'reason': reason})
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
            # Fetch the decryption request along with the related file info.
            request = self.client.from_('decryption_requests')\
                .select('*, files!inner(id, name)')\
                .eq('id', request_id)\
                .single()\
                .execute()

            if not request.data:
                print("Decryption request not found")
                return False

            file_id = request.data['files']['id']
            threshold = request.data['threshold']
            user_id = self.auth.get_user_id()

            # Retrieve the key share record for the current user.
            share_result = self.client.from_('key_shares')\
                .select('*')\
                .eq('file_id', file_id)\
                .eq('user_id', user_id)\
                .execute()
            if not share_result.data or len(share_result.data) == 0:
                raise ValueError("You don't have a key share for this file")
            share_record = share_result.data[0]

            # Retrieve user profile and verify cloud storage connection.
            user = self.client.from_('users')\
                .select('*')\
                .eq('id', user_id)\
                .single()\
                .execute()
            if not user.data.get('cloud_connected'):
                raise ValueError("Cloud storage not connected")

            # Check for cloud_path in the share record.
            cloud_path = share_record.get('cloud_path')
            if not cloud_path:
                print("Cloud path for key share not found")
                return False

            print("Retrieving your key share...")

            # Retrieve share data from cloud storage.
            share_data = None
            if user.data.get('cloud_provider') == 'google_drive':
                try:
                    share_data = self._retrieve_from_google_drive(
                        user.data['cloud_credentials'],
                        file_id=share_record['file_id'],
                        share_id=share_record['id']
                    )
                except Exception as cloud_error:
                    print(f"Failed to retrieve share from Google Drive: {str(cloud_error)}")
                    return False

            # Save the retrieved share data locally for decryption.
            cache_dir = Path("temp_shares") / request_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            share_path = cache_dir / f"share_{share_record['id']}.bin"
            with open(share_path, 'wb') as f:
                f.write(share_data)
            print(f"Share saved locally at: {share_path}")

            # Update the key share record to indicate retrieval.
            self.client.from_('key_shares').update({'status': 'retrieved'})\
                .eq('id', share_record['id'])\
                .execute()

            # Refresh the decryption request and increment current_shares.
            request_updated = self.client.from_('decryption_requests')\
                .select('*')\
                .eq('id', request_id)\
                .single()\
                .execute()
            current_shares = request_updated.data.get('current_shares', 0) + 1
            new_status = 'ready' if current_shares >= threshold else 'pending'

            # IMPORTANT: Use the header to avoid returning full row data.
            self.client.from_('decryption_requests').update({
                'current_shares': current_shares,
                'status': new_status
            }).eq('id', request_id).execute(headers={"Prefer": "return=minimal"})

            print(f"Decryption request updated: {current_shares} shares collected")
            if current_shares >= threshold:
                print("Threshold reached! Starting decryption...")
                self._process_decryption(request_id, file_id)
            else:
                print(f"Share submitted! {current_shares}/{threshold} shares collected")
            return True

        except Exception as e:
         print(f"Failed to submit key share: {str(e)}")
        return False


    def _retrieve_from_google_drive(self, cloud_creds: dict, file_id: str, share_id: str) -> bytes:
        """
        Retrieve the zipped share from Google Drive using the unique cloud_path,
        unzip it, and return the share binary.
        """
        try:
            credentials = Credentials(
                token=cloud_creds['token'],
                refresh_token=cloud_creds['refresh_token'],
                token_uri=cloud_creds['token_uri'],
                client_id=cloud_creds['client_id'],
                client_secret=cloud_creds['client_secret'],
                scopes=cloud_creds['scopes']
            )
            service = build('drive', 'v3', credentials=credentials)
            folder_name = 'SecureShare_KeyShares'
            folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            folder_results = service.files().list(q=folder_query, spaces='drive').execute()
            if not folder_results.get('files'):
                raise ValueError("Key share folder not found on Google Drive.")
            folder_id = folder_results['files'][0]['id']

            # Look for the specific share file using the provided cloud_path.
            query = f"'{folder_id}' in parents and name='{cloud_path}'"
            results = service.files().list(q=query, spaces='drive').execute()
            items = results.get('files', [])
            if not items:
                raise ValueError("Share file not found in Google Drive.")
            drive_file_id = items[0]['id']
            request_drive = service.files().get_media(fileId=drive_file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request_drive)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)
            with zipfile.ZipFile(fh, 'r') as zipf:
                names = zipf.namelist()
                if not names:
                    raise ValueError("Zip share file is empty.")
                share_data = zipf.read(names[0])
            if not share_data:
                raise ValueError("Retrieved share data is empty.")
            return share_data
        except Exception as e:
            raise ValueError(f"Failed to retrieve share from Google Drive: {str(e)}")


        def _process_decryption(self, request_id: str, file_id: str) -> bool:
            """Process file decryption when threshold is met."""
        try:
            shares_dir = Path("temp_shares") / request_id
            if not shares_dir.exists():
                raise ValueError("Share cache not found")
            collected_shares = []
            share_files = list(shares_dir.glob("share_*.bin"))
            for share_file in share_files:
                with open(share_file, 'rb') as f:
                    share_data = f.read()
                    share_id = share_file.stem.split('_')[1]
                    share_info = self.client.from_('key_shares')\
                        .select('*')\
                        .eq('id', share_id)\
                        .single()\
                        .execute()
                    collected_shares.append((share_info.data['share_index'], share_data))
            file = self.client.from_('files').select('*').eq('id', file_id).single().execute()
            encrypted_data = self.client.storage.from_('encrypted-files').download(f"{file_id}/{file.data['name']}")
            key = self.shamir.reconstruct_secret(collected_shares)
            decrypted_data = decrypt_file(encrypted_data, key, base64.b64decode(file.data['nonce']))
            output_dir = Path("temp_decrypted")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / file.data['name']
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            expiry_time = datetime.datetime.now() + datetime.timedelta(hours=24)
            expiry_path = output_dir / f"{file.data['name']}.expiry"
            with open(expiry_path, 'w') as f:
                f.write(expiry_time.isoformat())
            self.client.from_('files').update({'status': 'decrypted'})\
                .eq('id', file_id).execute()
            shutil.rmtree(shares_dir)
            print(f"File successfully decrypted! Available at: {output_path}")
            print("File will be available for 24 hours")
            return True
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def verify_encryption(self, file_path: str, org_id: str) -> bool:
        """Verify file encryption by attempting to read it."""
        try:
            encrypted_data = self.client.storage.from_('encrypted-files').download(file_path)
            for parser in [
                lambda x: open(x, 'r').read(),
                lambda x: Image.open(x) if Image else None,
                lambda x: PyPDF2.PdfReader(x) if PyPDF2 else None
            ]:
                try:
                    parser(io.BytesIO(encrypted_data))
                    return True
                except Exception:
                    continue
            return False
        except Exception as e:
            logger.error(f"Encryption verification failed: {e}")
            return False

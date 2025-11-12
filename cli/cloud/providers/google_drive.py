import datetime
import os
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def connect_google_drive(cli: "SecureShareCLI") -> None:
    """Connect Google Drive using OAuth flow."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI') or os.getenv('DEFAULT_REDIRECT_URI')

        if not client_id or not client_secret:
            raise ValueError("Google Drive credentials not found in environment variables")

        if not redirect_uri:
            raise ValueError("Google Drive redirect URI not configured in environment variables")

        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
            },
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        print(f"{Fore.CYAN}Opening browser for Google Drive authentication...{Style.RESET_ALL}")
        credentials = flow.run_local_server(
            authorization_prompt_message='Please visit this URL to authorize access:',
            success_message='Authentication successful! You may close this window.',
            open_browser=True,
            access_type='offline',
            prompt='consent'
        )

        creds_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }

        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        missing_fields = [field for field in required_fields if not creds_dict.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required credential fields: {', '.join(missing_fields)}")

        user_id = cli.auth.get_user_id()
        if not user_id:
            raise ValueError("User not authenticated")

        cli.client.from_('users').update({
            'cloud_connected': True,
            'cloud_provider': 'google_drive',
            'cloud_credentials': creds_dict,
            'updated_at': datetime.datetime.now().isoformat()
        }).eq('id', user_id).execute()

        service = build('drive', 'v3', credentials=credentials)
        _ = service.about().get(fields="user").execute()

        print(f"{Fore.GREEN}Successfully connected Google Drive!{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Failed to connect Google Drive: {e}{Style.RESET_ALL}")

    input("Press Enter to continue...")



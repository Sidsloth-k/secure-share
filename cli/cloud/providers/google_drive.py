import datetime
import os
import time
import threading
import webbrowser
from typing import TYPE_CHECKING
from urllib.parse import urlparse, parse_qs, quote
from http.server import HTTPServer, BaseHTTPRequestHandler

from colorama import Fore, Style
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

if TYPE_CHECKING:
    from main import SecureShareCLI


def connect_google_drive(cli: "SecureShareCLI") -> None:
    """Connect Google Drive using OAuth flow."""
    while True:
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

            # Normalize redirect_uri (remove trailing slashes, ensure consistent format)
            redirect_uri = redirect_uri.strip().rstrip('/')
            
            # Parse redirect URI to get port
            parsed_uri = urlparse(redirect_uri)
            port = parsed_uri.port or 8080
            
            # Reconstruct to ensure consistent format (no trailing slash)
            normalized_redirect_uri = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
            if parsed_uri.path and parsed_uri.path != '/':
                normalized_redirect_uri += parsed_uri.path.rstrip('/')
            redirect_uri = normalized_redirect_uri

            # Debug: Show what redirect_uri is being used
            print(f"\n{Fore.CYAN}=== Google Drive OAuth Configuration ==={Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Using redirect_uri: {redirect_uri}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}IMPORTANT: This must EXACTLY match what's registered in Google Cloud Console{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Check: APIs & Services > Credentials > Your OAuth 2.0 Client ID > Authorized redirect URIs{Style.RESET_ALL}\n")

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
            
            # Explicitly set redirect_uri on the flow object
            flow.redirect_uri = redirect_uri

            # Get authorization URL
            auth_url, state = flow.authorization_url(
                prompt='consent', 
                access_type='offline'
            )
            
            # Verify redirect_uri is in the URL
            parsed_auth_url = urlparse(auth_url)
            auth_params = parse_qs(parsed_auth_url.query)
            
            actual_redirect_uri_in_url = None
            if 'redirect_uri' in auth_params:
                actual_redirect_uri_in_url = auth_params['redirect_uri'][0]
                print(f"{Fore.GREEN}✓ redirect_uri found in authorization URL: {actual_redirect_uri_in_url}{Style.RESET_ALL}")
                
                # Check if it matches what we expect
                if actual_redirect_uri_in_url != redirect_uri:
                    print(f"{Fore.YELLOW}⚠ Warning: redirect_uri in URL ({actual_redirect_uri_in_url}) doesn't match expected ({redirect_uri}){Style.RESET_ALL}")
            else:
                # Manually add redirect_uri if it's missing
                print(f"{Fore.YELLOW}Warning: redirect_uri not found in auth URL, adding it...{Style.RESET_ALL}")
                encoded_redirect_uri = quote(redirect_uri, safe='')
                if '?' in auth_url:
                    auth_url += f"&redirect_uri={encoded_redirect_uri}"
                else:
                    auth_url += f"?redirect_uri={encoded_redirect_uri}"
            
            print(f"\n{Fore.CYAN}Opening browser for Google Drive authentication...{Style.RESET_ALL}")
            print(f"\nPlease visit this URL to authorize access:")
            print(f"{Fore.YELLOW}{auth_url}{Style.RESET_ALL}\n")
            
            # Show menu options
            print(f"{Fore.CYAN}Options:{Style.RESET_ALL}")
            print("1. Continue (browser will open automatically)")
            print("2. Retry (get new authorization URL)")
            print("0. Back to main menu")
            
            choice = input("\nEnter choice (or press Enter to continue): ").strip()
            
            if choice == '0':
                return
            elif choice == '2':
                continue  # Retry with new URL
            
            # Open browser
            webbrowser.open(auth_url)
            
            # Manual callback handler
            auth_code = None
            error_message = None
            
            class OAuthHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    nonlocal auth_code, error_message
                    query_params = parse_qs(urlparse(self.path).query)
                    
                    if 'code' in query_params:
                        auth_code = query_params['code'][0]
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Authentication successful!</h1><p>You may close this window.</p></body></html>')
                    elif 'error' in query_params:
                        error_message = query_params['error'][0]
                        self.send_response(400)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(f'<html><body><h1>Authentication failed: {error_message}</h1></body></html>'.encode())
                    else:
                        self.send_response(400)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Invalid request</h1></body></html>')
                
                def log_message(self, format, *args):
                    pass  # Suppress server logs
            
            # Start local server
            server = HTTPServer(('localhost', port), OAuthHandler)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                print(f"\nWaiting for authorization... (listening on {redirect_uri})")
                print("Press Ctrl+C to cancel")
                
                # Wait for callback (with timeout)
                timeout = 300  # 5 minutes
                start_time = time.time()
                while auth_code is None and error_message is None:
                    if time.time() - start_time > timeout:
                        raise TimeoutError("Authorization timeout. Please try again.")
                    time.sleep(0.5)
            finally:
                # Always shutdown server
                server.shutdown()
                server.server_close()
            
            if error_message:
                # Handle redirect_uri_mismatch error specifically
                if 'redirect_uri_mismatch' in error_message.lower() or 'redirect_uri' in error_message.lower():
                    print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
                    print(f"{Fore.RED}ERROR: redirect_uri_mismatch{Style.RESET_ALL}")
                    print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")
                    print(f"\n{Fore.YELLOW}The redirect URI in your request doesn't match Google Cloud Console.{Style.RESET_ALL}")
                    print(f"\n{Fore.CYAN}Redirect URI being used: {Fore.YELLOW}{redirect_uri}{Style.RESET_ALL}")
                    print(f"\n{Fore.CYAN}To fix this:{Style.RESET_ALL}")
                    print(f"1. Go to: {Fore.YELLOW}https://console.cloud.google.com/apis/credentials{Style.RESET_ALL}")
                    print(f"2. Select your OAuth 2.0 Client ID (the one with Client ID: {client_id[:20]}...)")
                    print(f"3. Under 'Authorized redirect URIs', add EXACTLY this URI:")
                    print(f"   {Fore.GREEN}{redirect_uri}{Style.RESET_ALL}")
                    print(f"4. Make sure there are NO trailing slashes or extra characters")
                    print(f"5. Click 'Save' and wait a few minutes for changes to propagate")
                    print(f"6. Try connecting again\n")
                    raise ValueError(f"redirect_uri_mismatch: {redirect_uri} is not registered in Google Cloud Console")
                else:
                    raise ValueError(f"Authentication failed: {error_message}")
            
            if not auth_code:
                raise ValueError("No authorization code received")
            
            # Exchange code for credentials
            # The redirect_uri is already set on the flow object
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials

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
            input("Press Enter to continue...")
            return

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Authentication cancelled.{Style.RESET_ALL}")
            return
        except Exception as e:
            error_str = str(e)
            print(f"\n{Fore.RED}Failed to connect Google Drive: {error_str}{Style.RESET_ALL}")
            
            # Check if it's a redirect_uri_mismatch error
            if 'redirect_uri_mismatch' in error_str.lower() or 'redirect_uri' in error_str.lower():
                print(f"\n{Fore.YELLOW}This is a redirect_uri_mismatch error.{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Make sure you've added the redirect URI to Google Cloud Console before retrying.{Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
            print("1. Retry")
            print("0. Back to main menu")
            
            choice = input("\nEnter choice: ").strip()
            if choice == '0':
                return
            # Continue loop to retry



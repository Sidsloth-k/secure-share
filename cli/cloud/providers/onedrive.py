import datetime
import os
import webbrowser
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def connect_onedrive(cli: "SecureShareCLI") -> None:
    """Connect Microsoft OneDrive via authorization code flow."""
    while True:
        try:
            import msal

            client_id = os.getenv('ONEDRIVE_CLIENT_ID')
            redirect_uri = os.getenv('ONEDRIVE_REDIRECT_URI') or os.getenv('DEFAULT_REDIRECT_URI')
            scopes = ['Files.ReadWrite.AppFolder']

            if not client_id:
                raise ValueError("OneDrive client ID not found in environment variables")

            if not redirect_uri:
                raise ValueError("OneDrive redirect URI not configured in environment variables")

            msal_app = msal.PublicClientApplication(
                client_id,
                authority="https://login.microsoftonline.com/common"
            )

            auth_url = msal_app.get_authorization_request_url(
                scopes,
                redirect_uri=redirect_uri
            )

            print(f"\n{Fore.CYAN}Opening browser for OneDrive authentication...{Style.RESET_ALL}")
            print(f"\nPlease visit this URL to authorize access:")
            print(f"{Fore.YELLOW}{auth_url}{Style.RESET_ALL}\n")
            webbrowser.open(auth_url)
            
            # Show menu options
            print(f"{Fore.CYAN}Options:{Style.RESET_ALL}")
            print("1. Continue (enter authorization code)")
            print("2. Retry (get new authorization URL)")
            print("0. Back to main menu")
            
            choice = input("\nEnter choice (or press Enter to continue): ").strip()
            
            if choice == '0':
                return
            elif choice == '2':
                continue  # Retry with new URL

            auth_code = input("\nEnter the authorization code: ").strip()
            
            if not auth_code:
                print(f"{Fore.YELLOW}No authorization code entered.{Style.RESET_ALL}")
                continue
                
            result = msal_app.acquire_token_by_authorization_code(
                auth_code,
                scopes,
                redirect_uri=redirect_uri
            )

            if 'error' in result:
                raise ValueError(f"Authentication failed: {result.get('error_description', result['error'])}")

            user_id = cli.auth.get_user_id()
            cli.client.table('users').update({
                'cloud_connected': True,
                'cloud_provider': 'onedrive',
                'cloud_credentials': {
                    'access_token': result['access_token'],
                    'refresh_token': result.get('refresh_token'),
                    'expires_in': result['expires_in']
                },
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', user_id).execute()

            print(f"{Fore.GREEN}Successfully connected OneDrive!{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Authentication cancelled.{Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"\n{Fore.RED}Failed to connect OneDrive: {e}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
            print("1. Retry")
            print("0. Back to main menu")
            
            choice = input("\nEnter choice: ").strip()
            if choice == '0':
                return
            # Continue loop to retry



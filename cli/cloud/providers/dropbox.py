import datetime
import os
import webbrowser
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def connect_dropbox(cli: "SecureShareCLI") -> None:
    """Connect Dropbox via OAuth flow."""
    while True:
        try:
            import dropbox

            app_key = os.getenv('DROPBOX_APP_KEY')
            app_secret = os.getenv('DROPBOX_APP_SECRET')

            if not app_key or not app_secret:
                raise ValueError("Dropbox credentials not found in environment variables")

            auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
                app_key,
                app_secret,
                token_access_type='offline'
            )

            auth_url = auth_flow.start()
            print(f"\n{Fore.CYAN}Opening browser for Dropbox authentication...{Style.RESET_ALL}")
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
                
            oauth_result = auth_flow.finish(auth_code)

            user_id = cli.auth.get_user_id()
            cli.client.table('users').update({
                'cloud_connected': True,
                'cloud_provider': 'dropbox',
                'cloud_credentials': {
                    'access_token': oauth_result.access_token,
                    'refresh_token': oauth_result.refresh_token,
                    'account_id': oauth_result.account_id
                },
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', user_id).execute()

            print(f"{Fore.GREEN}Successfully connected Dropbox!{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Authentication cancelled.{Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"\n{Fore.RED}Failed to connect Dropbox: {e}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
            print("1. Retry")
            print("0. Back to main menu")
            
            choice = input("\nEnter choice: ").strip()
            if choice == '0':
                return
            # Continue loop to retry



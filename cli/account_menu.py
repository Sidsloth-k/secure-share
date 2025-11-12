from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def handle_account_menu(cli: "SecureShareCLI") -> None:
    """Display account settings menu and handle user input."""
    while True:
        cli._clear_screen()
        print(f"{Fore.CYAN}===== ACCOUNT SETTINGS ====={Style.RESET_ALL}\n")

        # Get user profile and cloud status
        user_id = cli.auth.get_user_id()
        user_profile = cli.client.from_('users').select('*').eq('id', user_id).single().execute()

        if user_profile.data:
            profile = user_profile.data
            print(f"Email: {profile['email']}")
            print(f"Display Name: {profile['display_name']}")
            print("\nCloud Storage Status:")

            if profile['cloud_connected']:
                provider = profile['cloud_provider']
                provider_color = {
                    'google_drive': f"{Fore.BLUE}Google Drive{Style.RESET_ALL}",
                    'dropbox': f"{Fore.CYAN}Dropbox{Style.RESET_ALL}",
                    'onedrive': f"{Fore.GREEN}OneDrive{Style.RESET_ALL}"
                }.get(provider, provider)
                print(f"Connected to: {provider_color}")
                print(f"Status: {Fore.GREEN}Connected{Style.RESET_ALL}")
            else:
                print(f"Status: {Fore.YELLOW}Not Connected{Style.RESET_ALL}")

        print("\n1. Connect Cloud Storage")
        if user_profile.data.get('cloud_connected'):
            print("2. Disconnect Cloud Storage")
        print("0. Back to Main Menu")

        try:
            choice = input("\nEnter choice: ")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.YELLOW}Returning to previous menu...{Style.RESET_ALL}")
            break

        if choice == '1':
            if user_profile.data.get('cloud_connected'):
                print(f"{Fore.YELLOW}You are already connected to a cloud provider.{Style.RESET_ALL}")
                print("Please disconnect current provider before connecting a new one.")
                input("Press Enter to continue...")
            else:
                cli._connect_cloud_storage()
        elif choice == '2' and user_profile.data.get('cloud_connected'):
            cli._disconnect_cloud_storage()
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
            input("Press Enter to continue...")



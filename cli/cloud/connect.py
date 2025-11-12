from typing import TYPE_CHECKING

from colorama import Fore, Style

from cli.cloud.providers import (
    connect_google_drive,
    connect_dropbox,
    connect_onedrive,
)

if TYPE_CHECKING:
    from main import SecureShareCLI


def connect_cloud_storage(cli: "SecureShareCLI") -> None:
    """Handle cloud storage connection."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== CONNECT CLOUD STORAGE ====={Style.RESET_ALL}\n")

    user_id = cli.auth.get_user_id()
    if not user_id:
        print(f"{Fore.RED}You must be logged in to connect cloud storage{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    print("Select Cloud Provider:")
    print("1. Google Drive")
    print("2. Dropbox")
    print("3. Microsoft OneDrive")
    print("0. Back")

    choice = input("\nEnter choice: ")

    try:
        if choice == '1':
            connect_google_drive(cli)
        elif choice == '2':
            connect_dropbox(cli)
        elif choice == '3':
            connect_onedrive(cli)
    except Exception as e:
        print(f"{Fore.RED}Failed to connect cloud storage: {e}{Style.RESET_ALL}")
        input("Press Enter to continue...")



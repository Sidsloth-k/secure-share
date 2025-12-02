from typing import TYPE_CHECKING

from colorama import Fore, Style

from cli.exit_handler import exit_application

if TYPE_CHECKING:
    from main import SecureShareCLI


def handle_main_menu(cli: "SecureShareCLI") -> None:
    """Display main menu and handle user input."""
    while True:
        cli._clear_screen()
        print(f"{Fore.CYAN}===== SECURE FILE SHARING APPLICATION ====={Style.RESET_ALL}")

        if not cli.auth.is_authenticated():
            print("\n1. Login")
            print("2. Register")
            print("0. Exit")

            try:
                choice = input("\nEnter choice: ")
            except (KeyboardInterrupt, EOFError):
                exit_application(cli)

            if choice == '1':
                cli.login()
            elif choice == '2':
                cli.register()
            elif choice == '0':
                exit_application(cli)
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input("Press Enter to continue...")
        else:
            print("\n1. Organization Management")
            print("2. File Management")
            print("3. Account Settings")
            print("4. Log Out")
            print("0. Exit")

            try:
                choice = input("\nEnter choice: ")
            except (KeyboardInterrupt, EOFError):
                exit_application(cli)

            if choice == '1':
                cli.organization_menu()
            elif choice == '2':
                cli.file_menu()
            elif choice == '3':
                cli.account_menu()
            elif choice == '4':
                cli.auth.logout()
            elif choice == '0':
                exit_application(cli)
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input("Press Enter to continue...")



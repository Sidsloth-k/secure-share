from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def handle_organization_menu(cli: "SecureShareCLI") -> None:
    """Display organization menu and handle user input."""
    while True:
        cli._clear_screen()
        print(f"{Fore.CYAN}===== ORGANIZATION MANAGEMENT ====={Style.RESET_ALL}\n")

        organizations = cli.org_manager.get_user_organizations()

        if organizations:
            print("Your Organizations:")
            for i, org in enumerate(organizations, 1):
                print(f"{i}. {org['name']} ({org['member_count']} members) - {org['role']}")
        else:
            print("You are not a member of any organizations.")

        print("\n1. Create New Organization")
        print("2. Join Organization")
        print("3. View Organization Details")
        print("4. Manage Organization")
        print("0. Back to Main Menu")

        try:
            choice = input("\nEnter choice: ")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.YELLOW}Returning to main menu...{Style.RESET_ALL}")
            break

        if choice == '1':
            cli._create_organization()
        elif choice == '2':
            cli._join_organization()
        elif choice == '3':
            cli._view_organization(organizations)
        elif choice == '4':
            cli._manage_organization(organizations)
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
            input("Press Enter to continue...")



from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def create_organization(cli: "SecureShareCLI") -> None:
    """Handle organization creation."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== CREATE ORGANIZATION ====={Style.RESET_ALL}\n")

    name = input("Organization Name: ")
    if name:
        try:
            cli.org_manager.create_organization(name)
        except Exception as e:
            print(f"{Fore.RED}Failed to create organization: {e}{Style.RESET_ALL}")
        input("Press Enter to continue...")



from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def join_organization(cli: "SecureShareCLI") -> None:
    """Handle joining an organization."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== JOIN ORGANIZATION ====={Style.RESET_ALL}\n")

    print("Enter invite code (leave blank to go back).")
    invite_code = input("Invite Code: ").strip()

    if not invite_code:
        print(f"{Fore.YELLOW}Join cancelled.{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    try:
        cli.org_manager.join_organization(invite_code)
    except Exception as e:
        print(f"{Fore.RED}Failed to join organization: {e}{Style.RESET_ALL}")

    input("Press Enter to continue...")



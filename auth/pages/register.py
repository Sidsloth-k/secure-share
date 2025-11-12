import getpass
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def register_page(cli: "SecureShareCLI") -> None:
    """Render registration page and handle user registration."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== REGISTER ====={Style.RESET_ALL}\n")

    email = input("Email: ")
    display_name = input("Display Name: ")
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")

    if password != password_confirm:
        input(f"{Fore.RED}Passwords do not match.{Style.RESET_ALL} Press Enter to try again...")
        return

    if cli.auth.register(email, password, display_name):
        input("Press Enter to continue...")



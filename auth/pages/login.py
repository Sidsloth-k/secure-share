import getpass
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def login_page(cli: "SecureShareCLI") -> None:
    """Render login page and handle user login."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== LOGIN ====={Style.RESET_ALL}\n")

    email = input("Email: ")
    password = getpass.getpass("Password: ")

    if cli.auth.login(email, password):
        input(f"{Fore.GREEN}Login successful!{Style.RESET_ALL} Press Enter to continue...")
    else:
        input(f"{Fore.RED}Login failed.{Style.RESET_ALL} Press Enter to try again...")



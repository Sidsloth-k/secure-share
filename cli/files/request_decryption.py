from typing import TYPE_CHECKING, List, Dict

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def request_decryption(cli: "SecureShareCLI", org_id: str, files: List[Dict]) -> None:
    """Handle decryption request."""
    if not files:
        print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    print("\nSelect file to decrypt:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file['name']}")

    try:
        choice = int(input("\nEnter file number: "))
        file = files[choice - 1]
        reason = input("Enter reason for decryption (optional): ")
        cli.file_manager.request_decryption(file['id'], reason)
        input("Press Enter to continue...")
    except (ValueError, IndexError):
        print(f"{Fore.RED}Invalid file selection{Style.RESET_ALL}")
        input("Press Enter to continue...")



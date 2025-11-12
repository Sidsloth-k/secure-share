from typing import TYPE_CHECKING, List, Dict

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def check_decrypted_file(cli: "SecureShareCLI", org_id: str, files: List[Dict]) -> None:
    """Handle checking decrypted file status."""
    if not files:
        print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    print("\nSelect file to check:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file['name']}")

    try:
        choice = int(input("\nEnter file number: "))
        file = files[choice - 1]
        status = cli.file_manager.check_decrypted_file(file['id'])

        if status['status'] == 'decrypted':
            print(f"\nFile is decrypted and available at: {status['path']}")
            print(f"File expires in: {status['expires_in']}")
        else:
            print(f"\nFile status: {status['status']}")

        input("Press Enter to continue...")
    except (ValueError, IndexError):
        print(f"{Fore.RED}Invalid file selection{Style.RESET_ALL}")
        input("Press Enter to continue...")



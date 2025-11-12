from typing import TYPE_CHECKING, List, Dict

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def delete_file(cli: "SecureShareCLI", org_id: str, files: List[Dict]) -> None:
    """Handle file deletion."""
    if not files:
        print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    print("\nSelect file to delete:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file['name']}")

    try:
        choice = int(input("\nEnter file number: "))
        file = files[choice - 1]

        confirm = input(
            f"\n{Fore.RED}WARNING: This will permanently delete the file and all shares.{Style.RESET_ALL}\nType 'DELETE' to confirm: "
        )
        if confirm != 'DELETE':
            print("Deletion cancelled.")
            return

        cli.file_manager.delete_file(file['id'], org_id)
        print(f"{Fore.GREEN}File successfully deleted!{Style.RESET_ALL}")

    except ValueError as e:
        print(f"{Fore.RED}Invalid selection: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Deletion failed: {e}{Style.RESET_ALL}")

    input("Press Enter to continue...")



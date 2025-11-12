from typing import TYPE_CHECKING, List, Dict

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def verify_file_encryption(cli: "SecureShareCLI", org_id: str, files: List[Dict]) -> None:
    """Handle manual file encryption verification."""
    if not files:
        print(f"{Fore.YELLOW}No files available{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    print("\nSelect file to verify:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file['name']}")

    try:
        choice = int(input("\nEnter file number: "))
        file = files[choice - 1]

        result = cli.file_manager.verify_file_encryption(file['id'])

        print(f"\n{Fore.CYAN}Encryption Verification Results:{Style.RESET_ALL}")
        print(f"File: {result['name']}")
        print(f"Size: {result['size']} bytes")
        print(f"Entropy: {result['entropy']:.2f} bits/byte")
        print(f"Appears Encrypted: {Fore.GREEN if result['appears_encrypted'] else Fore.RED}{result['appears_encrypted']}{Style.RESET_ALL}")
        print(f"Share Distribution: {result['total_shares']}/{result['threshold']} shares")
        print(f"Current Status: {result['status']}")

    except (ValueError, IndexError) as e:
        print(f"{Fore.RED}Invalid file selection: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Verification failed: {e}{Style.RESET_ALL}")

    input("Press Enter to continue...")



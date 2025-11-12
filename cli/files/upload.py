import getpass
import os
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def upload_file(cli: "SecureShareCLI", org_id: str) -> None:
    """Handle file upload."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== UPLOAD FILE ====={Style.RESET_ALL}\n")

    # Check eligibility first
    eligibility = cli.org_manager.check_encryption_eligibility(org_id)
    if not eligibility['eligible']:
        print(f"{Fore.RED}Cannot upload file - Organization requirements not met:{Style.RESET_ALL}")
        if not eligibility['member_count_met']:
            print(f" - Need {eligibility['required_count']} members (current: {eligibility['member_count']})")
        if not eligibility['cloud_storage_met']:
            print(" - The following members need to connect cloud storage:")
            for member in eligibility['members_without_cloud']:
                print(f"   - {member['display_name']} ({member['email']})")
        input("\nPress Enter to continue...")
        return

    print("Choose upload method:")
    print("1. Enter file path")
    print("2. Select file using file dialog")
    print("0. Cancel")

    try:
        choice = input("\nEnter choice: ")
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Fore.YELLOW}Returning to file management menu...{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    if choice == '0':
        return

    file_path = None
    if choice == '1':
        file_path = input("Enter file path: ")
    elif choice == '2':
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.askopenfilename(
                title="Select file to upload",
                filetypes=[
                    ("All files", "*.*"),
                    ("Text files", "*.txt"),
                    ("PDF files", "*.pdf"),
                    ("Image files", "*.jpg *.jpeg *.png *.gif")
                ]
            )
            root.destroy()
            if not file_path:
                print(f"{Fore.YELLOW}File selection canceled{Style.RESET_ALL}")
                input("Press Enter to continue...")
                return

        except Exception as e:
            print(f"{Fore.RED}Failed to open file dialog: {e}{Style.RESET_ALL}")
            print("Please try entering the file path manually.")
            input("Press Enter to continue...")
            return
    else:
        print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    if not file_path:
        print(f"{Fore.YELLOW}No file selected{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    if not os.path.exists(file_path):
        print(f"{Fore.RED}File not found: {file_path}{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    print(f"\nSelected file:")
    print(f"Name: {file_name}")
    print(f"Size: {file_size} bytes")
    print(f"Path: {file_path}")

    confirm = input("\nProceed with this file? (y/n): ")
    if confirm.lower() != 'y':
        return

    threshold_input = input("\nEnter decryption threshold (minimum number of shares required): ")
    try:
        threshold = int(threshold_input)
        if threshold < 3:
            print(f"{Fore.RED}Threshold must be at least 3{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return
    except ValueError:
        print(f"{Fore.RED}Invalid threshold{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    password = getpass.getpass("Enter encryption password: ")
    confirm_password = getpass.getpass("Confirm encryption password: ")

    if password != confirm_password:
        print(f"{Fore.RED}Passwords do not match{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    try:
        cli.file_manager.upload_file(file_path, org_id, threshold, password)
        input("Press Enter to continue...")
    except Exception as e:
        print(f"{Fore.RED}Upload failed: {e}{Style.RESET_ALL}")
        input("Press Enter to continue...")



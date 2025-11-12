from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def handle_file_menu(cli: "SecureShareCLI") -> None:
    """Display file menu and handle user input."""
    while True:
        cli._clear_screen()
        print(f"{Fore.CYAN}===== FILE MANAGEMENT ====={Style.RESET_ALL}\n")

        organizations = cli.org_manager.get_user_organizations()

        if not organizations:
            print(f"{Fore.YELLOW}You must be a member of an organization to manage files.{Style.RESET_ALL}")
            input("Press Enter to continue...")
            break

        print("Select Organization:")
        for i, org in enumerate(organizations, 1):
            print(f"{i}. {org['name']} ({org['member_count']} members)")

        org_choice = input("\nEnter organization number (0 to go back): ")

        if org_choice == '0':
            break

        try:
            org_index = int(org_choice) - 1
            if org_index < 0 or org_index >= len(organizations):
                raise ValueError("Invalid organization index")

            selected_org = organizations[org_index]
            org_id = selected_org['id']

            # Check encryption eligibility
            eligibility = cli.org_manager.check_encryption_eligibility(org_id)

            while True:
                cli._clear_screen()
                print(f"{Fore.CYAN}===== FILE MANAGEMENT: {selected_org['name']} ====={Style.RESET_ALL}\n")

                if not eligibility['eligible']:
                    print(f"{Fore.YELLOW}Organization does not meet encryption requirements:{Style.RESET_ALL}")

                    if not eligibility['member_count_met']:
                        print(f" - Organization must have at least {eligibility['required_count']} members")
                        print(f"   (current: {eligibility['member_count']})")

                    if not eligibility['cloud_storage_met']:
                        print("\n The following members need to connect cloud storage:")
                        for member in eligibility['members_without_cloud']:
                            print(f" - {member['display_name']} ({member['email']})")
                    print("")

                files = cli.file_manager.list_files(org_id)

                if files:
                    print("Files:")
                    for i, file in enumerate(files, 1):
                        status_color = Fore.GREEN if file['status'] == 'available' else (
                            Fore.YELLOW if file['status'] == 'pending_decryption' else Fore.CYAN
                        )
                        print(f"{i}. {file['name']} ({file['size']} bytes) - "
                              f"Uploaded by: {file['uploader']} - "
                              f"Status: {status_color}{file['status']}{Style.RESET_ALL}")
                else:
                    print("No files found in this organization.")

                print("\n1. Upload and Encrypt File")
                print("2. Request File Decryption")
                print("3. Submit Key Share")
                print("4. Check Decrypted File")
                print("5. Verify File Encryption")
                print("6. Delete File")
                print("0. Back to Organizations")

                choice = input("\nEnter choice: ")

                if choice == '1':
                    if eligibility['eligible']:
                        cli._upload_file(org_id)
                    else:
                        print(f"{Fore.RED}Organization does not meet requirements for encryption{Style.RESET_ALL}")
                        input("Press Enter to continue...")
                elif choice == '2':
                    cli._request_decryption(org_id, files)
                elif choice == '3':
                    cli._submit_key_share(org_id)
                elif choice == '4':
                    cli._check_decrypted_file(org_id, files)
                elif choice == '5':
                    cli._verify_file_encryption(org_id, files)
                elif choice == '6':
                    cli._delete_file(org_id, files)
                elif choice == '0':
                    break
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                    input("Press Enter to continue...")

        except (ValueError, IndexError):
            print(f"{Fore.RED}Invalid organization selection{Style.RESET_ALL}")
            input("Press Enter to continue...")



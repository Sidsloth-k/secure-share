from typing import TYPE_CHECKING, List, Dict

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def manage_organization(cli: "SecureShareCLI", organizations: List[Dict]) -> None:
    """Handle admin organization management."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== MANAGE ORGANIZATION ====={Style.RESET_ALL}\n")

    admin_orgs = [org for org in organizations if org['role'] == 'admin']

    if not admin_orgs:
        print(f"{Fore.YELLOW}You are not an admin of any organizations.{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    print("Select organization to manage:")
    for i, org in enumerate(admin_orgs, 1):
        print(f"{i}. {org['name']} ({org['member_count']} members)")

    try:
        choice = int(input("\nEnter organization number: "))
        if choice < 1 or choice > len(admin_orgs):
            raise ValueError("Invalid organization number")

        org = admin_orgs[choice - 1]
        org_id = org['id']

        while True:
            cli._clear_screen()
            print(f"{Fore.CYAN}===== MANAGE {org['name'].upper()} ====={Style.RESET_ALL}\n")
            members = cli.org_manager.list_organization_members(org_id)

            print("Members:")
            for i, member in enumerate(members, 1):
                role_color = Fore.GREEN if member['role'] == 'admin' else Fore.BLUE
                print(f"{i}. {member['display_name']} ({member['email']}) - {role_color}{member['role']}{Style.RESET_ALL}")

            print("\nAdmin Actions:")
            print("1. Remove Member")
            print("0. Back")

            try:
                admin_choice = input("\nEnter choice: ")
            except (KeyboardInterrupt, EOFError):
                print(f"\n{Fore.YELLOW}Returning to previous menu...{Style.RESET_ALL}")
                break

            if admin_choice == '1':
                member_num = int(input("Enter member number to remove: "))
                if member_num < 1 or member_num > len(members):
                    print(f"{Fore.RED}Invalid member number{Style.RESET_ALL}")
                else:
                    member = members[member_num - 1]
                    if member['id'] == cli.auth.get_user_id():
                        print(f"{Fore.RED}You cannot remove yourself from the organization{Style.RESET_ALL}")
                    else:
                        confirm = input(f"Are you sure you want to remove {member['display_name']}? (y/n): ")
                        if confirm.lower() == 'y':
                            try:
                                cli.org_manager.remove_member(org_id, member['id'])
                                print(f"{Fore.GREEN}Member removed successfully{Style.RESET_ALL}")
                            except Exception as e:
                                print(f"{Fore.RED}Failed to remove member: {e}{Style.RESET_ALL}")
                input("Press Enter to continue...")
            elif admin_choice == '0':
                break
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                input("Press Enter to continue...")

    except (ValueError, IndexError):
        print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
        input("Press Enter to continue...")



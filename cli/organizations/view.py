from typing import TYPE_CHECKING, List, Dict

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def view_organization(cli: "SecureShareCLI", organizations: List[Dict]) -> None:
    """Handle viewing organization details."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== VIEW ORGANIZATION ====={Style.RESET_ALL}\n")

    if not organizations:
        print(f"{Fore.YELLOW}You are not a member of any organizations.{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return

    print("Select organization to view:")
    for i, org in enumerate(organizations, 1):
        print(f"{i}. {org['name']}")

    try:
        choice = int(input("\nEnter organization number: "))
        if choice < 1 or choice > len(organizations):
            raise ValueError("Invalid organization number")

        org = organizations[choice - 1]
        org_id = org['id']
        org_role = org.get('role')

        while True:
            latest_org = cli.org_manager.get_organization(org_id) or {}
            members = cli.org_manager.list_organization_members(org_id)
            member_count = len(members)

            name = latest_org.get('name', org.get('name'))
            invite_code = latest_org.get('invite_code', org.get('invite_code', 'N/A'))
            invites_enabled = latest_org.get('invite_enabled', org.get('invite_enabled', False))

            cli._clear_screen()
            print(f"{Fore.CYAN}===== ORGANIZATION DETAILS ====={Style.RESET_ALL}\n")
            print(f"Name: {name}")
            print(f"Member Count: {member_count}")
            print(f"Invite Code: {invite_code}")
            print(f"Invites Enabled: {'Yes' if invites_enabled else 'No'}")

            if members:
                print("\nMembers:")
                for member in members:
                    role_color = Fore.GREEN if member['role'] == 'admin' else Fore.BLUE
                    print(f"- {member['display_name']} ({member['email']}) - Role: {role_color}{member['role']}{Style.RESET_ALL}")
            else:
                print("\nNo members found.")

            if org_role == 'admin':
                print("\nAdmin Options:")
                print("1. Toggle Invites")
                print("2. Regenerate Invite Code")
                print("0. Back")

                try:
                    admin_choice = input("\nEnter choice: ")
                except (KeyboardInterrupt, EOFError):
                    print(f"\n{Fore.YELLOW}Returning to previous menu...{Style.RESET_ALL}")
                    break
                if admin_choice == '1':
                    new_state = not invites_enabled
                    cli.org_manager.toggle_invites(org_id, new_state)
                    input("Press Enter to refresh details...")
                elif admin_choice == '2':
                    cli.org_manager.regenerate_invite_code(org_id)
                    input("Press Enter to refresh details...")
                elif admin_choice == '0':
                    break
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                    input("Press Enter to continue...")
            else:
                input("Press Enter to continue...")
                break

    except (ValueError, IndexError):
        print(f"{Fore.RED}Invalid organization selection{Style.RESET_ALL}")
        input("Press Enter to continue...")



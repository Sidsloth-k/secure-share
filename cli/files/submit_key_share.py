import datetime
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def submit_key_share(cli: "SecureShareCLI", org_id: str) -> None:
    """Handle key share submission."""
    cli._clear_screen()
    print(f"{Fore.CYAN}===== SUBMIT KEY SHARE ====={Style.RESET_ALL}\n")

    try:
        requests = (
            cli.client.from_('decryption_requests')
            .select('*, files!inner(name, organization_id, id), users!requester_id(display_name)')
            .eq('status', 'pending')
            .eq('files.organization_id', org_id)
            .execute()
        )

        if not requests.data:
            print(f"{Fore.YELLOW}No pending decryption requests found.{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return

        print("Pending Decryption Requests:")
        for i, req in enumerate(requests.data, 1):
            file_name = req['files']['name']
            requester = req['users']['display_name']
            shares = f"{req['current_shares']}/{req['threshold']}"
            
            # Handle timezone-aware and timezone-naive datetimes
            expires_str = req['expires_at']
            if isinstance(expires_str, str):
                expires = datetime.datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            else:
                expires = expires_str
            
            # Ensure both datetimes are timezone-aware or both are naive
            now = datetime.datetime.now(datetime.timezone.utc) if expires.tzinfo else datetime.datetime.now()
            if expires.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=datetime.timezone.utc)
            elif not expires.tzinfo and now.tzinfo:
                expires = expires.replace(tzinfo=datetime.timezone.utc)
            
            time_left = expires - now
            hours_left = time_left.total_seconds() / 3600

            print(f"\n{i}. File: {file_name}")
            print(f"   Requested by: {requester}")
            print(f"   Shares collected: {shares}")
            print(f"   Expires in: {hours_left:.1f} hours")
            if req.get('message'):
                print(f"   Reason: {req['message']}")

        choice = input("\nEnter request number (0 to cancel): ")
        if choice == '0':
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(requests.data):
                selected_request = requests.data[index]
                file_id = selected_request['files']['id']
                print(f"\n{Fore.CYAN}Retrieving your key share...{Style.RESET_ALL}")

                user_id = cli.auth.get_user_id()
                user = (
                    cli.client.from_('users').select('*').eq('id', user_id).single().execute()
                )

                if not user.data.get('cloud_connected'):
                    print(f"{Fore.RED}You need to connect your cloud storage first{Style.RESET_ALL}")
                    return

                existing_share = (
                    cli.client.from_('key_shares')
                    .select('status')
                    .eq('file_id', file_id)
                    .eq('user_id', user_id)
                    .eq('status', 'retrieved')
                    .execute()
                )

                if existing_share.data:
                    print(f"{Fore.YELLOW}You have already submitted your share for this file{Style.RESET_ALL}")
                    return

                try:
                    cli.file_manager.submit_key_share(selected_request['id'])
                    print(f"{Fore.GREEN}Share submitted successfully!{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Failed to submit share: {str(e)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")

        except ValueError:
            print(f"{Fore.RED}Invalid input{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Error retrieving decryption requests: {str(e)}{Style.RESET_ALL}")

    input("Press Enter to continue...")



import datetime
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def disconnect_cloud_storage(cli: "SecureShareCLI") -> None:
    """Handle cloud storage disconnection."""
    try:
        user_id = cli.auth.get_user_id()

        cli.client.from_('users').update({
            'cloud_connected': False,
            'cloud_provider': None,
            'cloud_credentials': None,
            'updated_at': datetime.datetime.now().isoformat()
        }).eq('id', user_id).execute()

        print(f"{Fore.GREEN}Successfully disconnected cloud storage!{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Failed to disconnect cloud storage: {e}{Style.RESET_ALL}")

    input("Press Enter to continue...")



from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from main import SecureShareCLI


def exit_application(cli: "SecureShareCLI" = None) -> None:
    """
    Exit the application with a friendly message.

    If a CLI instance is provided and a user is logged in, this will also
    perform a logout to clear the session from Supabase and local storage
    before exiting.
    """
    try:
        if cli is not None and getattr(cli, "auth", None) is not None:
            cli.auth.logout()
    except Exception:
        # Best-effort logout; exit regardless
        pass

    print(f"\n{Fore.YELLOW}Exiting application...{Style.RESET_ALL}")
    raise SystemExit(0)

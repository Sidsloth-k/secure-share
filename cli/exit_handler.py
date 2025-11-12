from colorama import Fore, Style


def exit_application() -> None:
    """Exit the application immediately with a friendly message."""
    print(f"\n{Fore.YELLOW}Exiting application...{Style.RESET_ALL}")
    raise SystemExit(0)



import os


def clear_screen() -> None:
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')



import sys
from typing import NoReturn

_warning_mode = False


def set_warning_mode(enabled: bool) -> None:
    global _warning_mode
    _warning_mode = enabled


def Warning(message: str) -> None:
    if _warning_mode:
        print("Warning:", message)


def WarnAndExit(message: str) -> NoReturn:
    print(message)
    print("Exiting.")
    sys.exit()

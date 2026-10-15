class DiagnosticsReporter:
    def __init__(self, warning_mode: bool = False, debug_mode: bool = False) -> None:
        self._warning_mode = warning_mode
        self._debug_mode = debug_mode

    def warn(self, message: str) -> None:
        if self._warning_mode:
            print("Warning:", message)

    def debug(self, message: str) -> None:
        if self._debug_mode:
            print(message)

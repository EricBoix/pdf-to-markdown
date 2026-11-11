import logging


class DiagnosticsReporter:
    _logger = logging.getLogger("pdf_to_markdown")

    def warn(self, message: str) -> None:
        self._logger.warning(message)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

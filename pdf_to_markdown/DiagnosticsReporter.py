import logging


class DiagnosticsReporter:
    _logger = logging.getLogger("pdf_to_markdown")

    @classmethod
    def default_if_none(
        cls, diagnostics: "DiagnosticsReporter | None"
    ) -> "DiagnosticsReporter":
        """The given reporter, or a default one when none is given."""
        return diagnostics if diagnostics is not None else cls()

    def warn(self, message: str) -> None:
        self._logger.warning(message)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

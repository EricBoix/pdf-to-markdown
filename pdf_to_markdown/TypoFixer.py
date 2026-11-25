import re

from .DiagnosticsReporter import DiagnosticsReporter
from .PageInfo import TypoFix


class TypoFixer:
    """Corrects the typos that the pdf extraction produced in the text of a page.

    The typos to fix are declared per page by the StructuralInfo (see PageInfo).
    """

    def __init__(self, diagnostics: DiagnosticsReporter | None = None) -> None:
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)

    def fix(self, extracted_page, typo_fixes: tuple[TypoFix, ...]) -> None:
        """Apply the typo fixes, in order, on the text of the extracted page."""
        page_number = extracted_page.page_number
        for typo_fix in typo_fixes:
            typo = typo_fix.typo
            fixed_text, substitution_count = re.subn(
                typo, typo_fix.fix, extracted_page.text
            )
            if substitution_count == 0:
                self._diagnostics.warn(
                    f"Couldn't find typo in extracted page number {page_number}:"
                )
                self._diagnostics.warn(f"  - typo: {typo}")
                self._diagnostics.warn(f"  - page text: {extracted_page.text}")
                continue
            extracted_page.text = fixed_text
            self._diagnostics.debug(f"Typo fixed on page {page_number}")

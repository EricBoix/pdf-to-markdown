from .TypoRule import TypoRule


class LayoutTextCarriesIndentationAndColumns(TypoRule):
    """The text that pypdf extracts in layout mode keeps what the patterns of a
    book read: the indentation of a line, the centering of a title, the columns
    of a table.

    Action site: TextExtractor.extract_all. When pypdf cannot extract a page in
    layout mode it falls back to plain text, which has none of it: that is the
    trap, reported with the page.
    """

    def contradicted_by_fallback(self, page_number: int) -> str:
        """What to report about a page extracted as plain text."""
        return (
            f"The rule {self.name} is declared to hold but page {page_number} "
            "could not be extracted in layout mode: it is plain text, without "
            "indentation, centering or columns."
        )

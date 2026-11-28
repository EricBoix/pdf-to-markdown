from ..Model import PageBreak
from .TypoRule import TypoRule


class ReadingOrderIsLineOrder(TypoRule):
    """The reading order of a page is the extractor's line order (top to bottom,
    one text flow).

    The converter relies on it everywhere it reads the text of a page. Trap: the
    pages of the page breaks of the document must strictly increase (see
    PageBreakInserter); the order inside a page cannot be checked (see
    docs/rules_configurable.md).
    """

    def order_violations(
        self, page_breaks_with_context: list[tuple[PageBreak, str]]
    ) -> list[str]:
        """What contradicts the rule in the page breaks of a document, given in
        reading order each with a description of what it stands before: a page
        that comes back or comes twice, i.e. a document not in the order of its
        pages (e.g. a text moved across a page break)."""
        violations = []
        for (previous, previous_before), (current, current_before) in zip(
            page_breaks_with_context, page_breaks_with_context[1:]
        ):
            previous_pdf_page = previous.page_layout.page_number + 1
            current_pdf_page = current.page_layout.page_number + 1
            if current_pdf_page <= previous_pdf_page:
                violations.append(
                    f"The rule {self.name} is declared to hold but the page break "
                    f"to pdf page {current_pdf_page} ({current_before}) "
                    f"follows the one to pdf page {previous_pdf_page} "
                    f"({previous_before}): the pages are not in order."
                )
        return violations

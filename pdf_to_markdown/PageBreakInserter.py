from .DiagnosticsReporter import DiagnosticsReporter
from .Errors import ConverterError
from .Model import (
    DocumentHierarchicalLevel,
    Heading,
    PageBreak,
    Paragraph,
    Table,
)
from .PageLayout import PageLayout
from .typo_rules import ReadingOrderIsLineOrder


class PageBreakInserter:
    """Puts the page breaks (see PageBreak) in a document that is built.

    It is the last pass of the construction of a document: once the paragraphs
    spreading over two pages are reconstituted, the pages of the document are
    read in reading order. A page break is put before each element that is not on
    the page of what precedes it, and before each sentence of a paragraph that is
    not on the page of the previous sentence. What an element is on is the page
    of its layout (the one of its first sentence for a paragraph, a paragraph
    without sentences and a table without rows are not written, hence not
    counted); an element without layout leaves the page as it is.

    The pages of the page breaks must then strictly increase: a page that comes
    twice, or a page that comes back, means that the document is not in the order
    of its pages (e.g. a text moved across a page break). This is the trap of the
    rule ReadingOrderIsLineOrder, which the structural information hands over
    when the document holds it (*reading_order_rule*, None: the order of the pages
    is not checked). It is reported as a warning, or as an error when *strict* is
    set (meant for the tests).
    """

    def __init__(
        self,
        reading_order_rule: ReadingOrderIsLineOrder | None = None,
        diagnostics: DiagnosticsReporter | None = None,
        strict: bool = False,
    ) -> None:
        self._reading_order_rule = reading_order_rule
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)
        self._strict = strict
        self._current_page_number: int | None = None
        # The page breaks in reading order, with what they stand before
        self._page_breaks: list[tuple[PageBreak, str]] = []
        # What is wrong with the order of the pages, as messages
        self.violations: list[str] = []

    def insert_page_breaks(self, document: DocumentHierarchicalLevel) -> None:
        """Put the page breaks in the document (those that it already has are
        replaced), then check the order of the pages."""
        self._current_page_number = None
        self._page_breaks = []
        self.violations = []
        self._insert_in_level(document)
        self._check_the_order_of_the_pages()

    def _page_break_for(
        self, layout: PageLayout | None, before: str
    ) -> PageBreak | None:
        """The page break to put before a text of the given layout, None when that
        text is on the page of the text before it (or when its page is not
        known). The text is then the one before the next."""
        if layout is None or layout.page_number == self._current_page_number:
            return None
        self._current_page_number = layout.page_number
        page_break = PageBreak(layout)
        self._page_breaks.append((page_break, before))
        return page_break

    @staticmethod
    def _layout_of(sublevel) -> PageLayout | None:
        """The page that a sublevel starts on, None when it does not stand in the
        markdown (or when it does not tell)."""
        if isinstance(sublevel, Paragraph):
            sentences = sublevel.get_sentences()
            return sentences[0].page_layout if sentences else None
        if isinstance(sublevel, Table):
            return sublevel.page_layout if sublevel.rows else None
        return getattr(sublevel, "page_layout", None)

    @staticmethod
    def _description_of(sublevel) -> str:
        name = getattr(sublevel, "name", None)
        return (
            f"{type(sublevel).__name__} {name!r}" if name else type(sublevel).__name__
        )

    def _insert_in_level(self, level: DocumentHierarchicalLevel) -> None:
        # (The page breaks that the level already holds are not elements: they
        # are left aside, and put again where they belong.)
        sublevels = level.get_sublevels()
        if not sublevels:
            return
        with_page_breaks = []
        for sublevel in sublevels:
            page_break = self._page_break_for(
                self._layout_of(sublevel), "before " + self._description_of(sublevel)
            )
            if page_break is not None:
                page_break.set_owning_hierarchical_level(level)
                with_page_breaks.append(page_break)
            with_page_breaks.append(sublevel)
            if isinstance(sublevel, Paragraph):
                self._insert_in_paragraph(sublevel)
            elif isinstance(sublevel, DocumentHierarchicalLevel):
                self._insert_in_level(sublevel)
        level.sublevels = with_page_breaks

    def _insert_in_paragraph(self, paragraph: Paragraph) -> None:
        """The page of the first sentence was dealt with by the owner."""
        sentences = paragraph.get_sentences()
        if not sentences:
            return
        with_page_breaks = [sentences[0]]
        for sentence in sentences[1:]:
            page_break = self._page_break_for(
                sentence.page_layout,
                f"inside a paragraph, before the sentence {sentence.text[:40]!r}",
            )
            if page_break is not None:
                page_break.set_owning_hierarchical_level(paragraph)
                with_page_breaks.append(page_break)
            with_page_breaks.append(sentence)
        paragraph.sublevels = with_page_breaks

    def _check_the_order_of_the_pages(self) -> None:
        # Rule ReadingOrderIsLineOrder, see docs/rules_configurable.md
        if self._reading_order_rule is not None:
            self.violations = self._reading_order_rule.order_violations(
                self._page_breaks
            )
        for violation in self.violations:
            self._diagnostics.warn(violation)
        if self.violations and self._strict:
            raise ConverterError("\n".join(self.violations))

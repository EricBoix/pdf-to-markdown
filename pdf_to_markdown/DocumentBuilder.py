from abc import ABC, abstractmethod
from typing import Protocol

from .Model import (
    TopLevelChapterOfParagraphs,
    SubChapterOfParagraphs,
    DocumentHierarchicalLevel,
    DocumentHierarchicalRoot,
    SuperChapter,
    Paragraph,
    BlockQuoteParagraph,
    Sentence,
    Table,
)
from .PageLayout import PageLayout
from .StructuralInfoBase import StructuralInfoBase
from .DiagnosticsReporter import DiagnosticsReporter
from .Errors import ConverterError
from .LevelBreaker import LevelBreaker
from .SentenceBreaker import SentenceBreaker
from .TextSanitizer import TextSanitizer
from .ParagraphMerger import ParagraphMerger
from .BlockquoteDeduplicator import BlockquoteDeduplicator
from .PageBreakInserter import PageBreakInserter
from .SectionDropper import SectionDropper
from .TableRegistry import SpanningCellText, TableRegistry
from .typo_rules import HeadingIsOnItsPrintedPage


class ContentWithLayout(Protocol):
    """Protocol for content with page layout."""

    text: str
    page_layout: PageLayout


class DocumentBuilder(TextSanitizer, ABC):
    """Builds document hierarchy by breaking levels into sublevels."""

    def __init__(
        self,
        document: DocumentHierarchicalRoot,
        structural_info: StructuralInfoBase,
        diagnostics: DiagnosticsReporter | None = None,
    ) -> None:
        self.document = document
        self.structural_info = structural_info
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)
        # The tables cut out of the pages while this document is built: they
        # belong to this document only, not to the structural information.
        self._table_registry = TableRegistry()
        self._paragraph_merger = ParagraphMerger(
            structural_info, diagnostics=self._diagnostics
        )
        self._section_dropper = SectionDropper(
            structural_info, diagnostics=self._diagnostics
        )
        self._blockquote_deduplicator = BlockquoteDeduplicator(
            diagnostics=self._diagnostics
        )
        self._page_break_inserter = PageBreakInserter(
            reading_order_rule=structural_info.rule_if_holds("ReadingOrderIsLineOrder"),
            diagnostics=self._diagnostics,
        )

    def build_document(self) -> None:
        """Build the Document object out of converter extracted chapters."""
        self.break_document_into_chapters()  # Calling the derived version
        for chapter in self.document.get_chapters():
            self.break_level(chapter)
        # Dropping the sections first prevents a paragraph from being glued to
        # the text of a dropped section.
        self._section_dropper.drop_sections(self.document)
        # The blockquotes first: when a paragraph is merged the blockquotes
        # between its halves are moved, they must then be whole.
        for top_level_chapter in self.document.get_chapters():
            self._paragraph_merger.reconstitute_blockquotes_spreading_over_two_pages(
                top_level_chapter
            )
        for top_level_chapter in self.document.get_chapters():
            self._paragraph_merger.reconstitute_paragraphs_spreading_over_two_pages(
                top_level_chapter
            )
        # Once the paragraphs spreading over two pages are reconstituted the
        # blockquotes repeating a paragraph can be told apart.
        self._blockquote_deduplicator.remove_duplicated_blockquotes(self.document)
        # Last, once the order of the text is final: the page breaks stand
        # between what is on different pages.
        self._page_break_inserter.insert_page_breaks(self.document)

    @abstractmethod
    def break_document_into_chapters(self) -> None:
        """Break document into chapters. Must be implemented by subclass."""
        pass

    def break_paragraph_into_sentences(self, paragraph: Paragraph) -> None:
        paragraph_layout = paragraph.page_layout

        if paragraph.text is None:
            raise ConverterError(
                "Error: trying to break a paragraph into sentences but "
                "the paragraph text is None."
            )
        # (The boundary apostrophes of the sentences are preserved as-is, see
        # SentenceBreaker.)
        for new_sentence_text in SentenceBreaker.break_into_sentences(paragraph.text):
            new_sentence_layout = paragraph_layout.__copy__()
            new_sentence = Sentence(new_sentence_text, new_sentence_layout)
            paragraph.add_sublevel(new_sentence)
            paragraph.renumber_sublevels()

    def break_table(self, table: Table) -> None:
        """A table is not broken into sentences: its cell texts are sanitized."""

        def sanitize_cell(cell_text: str) -> str:
            sanitized_text = self.normalize_newlines_and_multiple_whitespaces(cell_text)
            if isinstance(cell_text, SpanningCellText):
                return SpanningCellText(sanitized_text)
            return sanitized_text

        table.rows = [[sanitize_cell(cell) for cell in row] for row in table.rows]
        if table.caption:
            table.caption = sanitize_cell(table.caption)

    def _heading_rule(self) -> HeadingIsOnItsPrintedPage:
        """The implicit rule HeadingIsOnItsPrintedPage (always true), from the
        rules of the structural information."""
        return self.structural_info.rule_register.get("HeadingIsOnItsPrintedPage")

    def break_any_level_chapter_into_paragraphs(
        self, chapter, contents: list[ContentWithLayout] | None = None
    ) -> None:
        """The chapter argument can be of any level e.g. a SuperChapter or a ChapterOfParagraphs..."""
        breaker = LevelBreaker(
            level=chapter,
            level_splitter=self.structural_info.chapter_to_paragraph_splitter(),
            sublevel_factory=Paragraph,
            break_level_callback=self.break_level,
            break_paragraphs_callback=self.break_any_level_chapter_into_paragraphs,
            heading_rule=self._heading_rule(),
            diagnostics=self._diagnostics,
            table_registry=self._table_registry,
        )
        breaker.break_into_sublevels(contents)
        chapter.renumber_sublevels()

    def break_superchapter_into_chapters(self, chapter: SuperChapter) -> None:
        def subchapter_factory(layout: PageLayout) -> SubChapterOfParagraphs:
            subchapter = SubChapterOfParagraphs("")
            subchapter.page_layout = layout
            return subchapter

        breaker = LevelBreaker(
            level=chapter,
            level_splitter=self.structural_info.superchapter_to_chapter_splitter(),
            sublevel_factory=subchapter_factory,
            break_level_callback=self.break_level,
            break_paragraphs_callback=self.break_any_level_chapter_into_paragraphs,
            heading_rule=self._heading_rule(),
            diagnostics=self._diagnostics,
        )
        breaker.break_into_sublevels()
        chapter.renumber_sublevels()

    def break_level(self, level: DocumentHierarchicalLevel) -> None:
        LEVEL_HANDLERS = {
            Paragraph: self.break_paragraph_into_sentences,
            BlockQuoteParagraph: self.break_paragraph_into_sentences,
            Table: self.break_table,
            TopLevelChapterOfParagraphs: self.break_any_level_chapter_into_paragraphs,
            SubChapterOfParagraphs: self.break_any_level_chapter_into_paragraphs,
            SuperChapter: self.break_superchapter_into_chapters,
        }
        handler = LEVEL_HANDLERS.get(type(level))
        if handler:
            handler(level)
            return
        raise ConverterError(f"Level of type {type(level)} has no break handler.")

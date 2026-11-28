from pypdf import PdfReader

from .ExtractedPage import ExtractedPage
from .Model import TopLevelChapter
from .PageLayout import PageLayout
from .TableExtractor import TableExtractor
from .TableRegistry import TableRegistry
from .TextExtractor import TextExtractor
from .TextSanitizer import TextSanitizer
from .TypoFixer import TypoFixer
from .DiagnosticsReporter import DiagnosticsReporter
from .Errors import ConverterError


class DocumentBreaker:
    """
    Breaks a PDF document into chapters by iterating over pages.
    Handles PDF reading, text extraction, and chapter breaking.

    The tables cut out of the pages are kept in the given table registry.
    """

    def __init__(
        self,
        pdf_filename,
        document,
        structural_info,
        table_registry: TableRegistry,
        diagnostics: DiagnosticsReporter | None = None,
    ) -> None:
        self.document = document
        self.structural_info = structural_info
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)
        self.chapter_splitter = structural_info.get_chapter_splitter()

        # Parse PDF and validate
        self.reader = PdfReader(pdf_filename)
        self._validate_all_pages()

        # Pre-extract all page texts
        text_extractor = TextExtractor(
            self.reader, structural_info, diagnostics=self._diagnostics
        )
        self.extracted_texts = text_extractor.extract_all()
        self.removed_first_line_indentations = (
            text_extractor.removed_first_line_indentations
        )
        self.table_extractor = TableExtractor(
            structural_info, table_registry, diagnostics=self._diagnostics
        )
        self.typo_fixer = TypoFixer(self._diagnostics)

    def _validate_all_pages(self) -> None:
        """Perform all upfront page validation."""
        if len(self.reader.pages) != self.structural_info.total_page_number:
            raise ConverterError(
                f"Erroneous number of pages: was expecting "
                f"{self.structural_info.total_page_number} but got {len(self.reader.pages)}"
            )
        for page_number in range(self.structural_info.total_page_number):
            self._validate_page(page_number)

    def _validate_page(self, page_number) -> None:
        """Validate a single page."""
        self._validate_reader_page_coherence(page_number)
        self._validate_page_structure(page_number)

    def _validate_reader_page_coherence(self, page_number) -> None:
        """Validate reader page number matches expected."""
        original_reader_page = self.reader.pages[page_number]
        original_reader_page_number = self.reader.get_page_number(original_reader_page)
        if page_number != original_reader_page_number:
            self._diagnostics.warn(
                f"Python page number does not match pypdf::reader page number:\n"
                f"   - Python page number:  {page_number}\n"
                f"   - pypdf::reader page number: {original_reader_page_number}"
            )

    def _validate_page_structure(self, page_number) -> None:
        """Validate page has required structural info.

        The declarations of all the pages are checked when the first page is
        asked for, see StructuralInfoBase.page_info."""
        self.structural_info.page_info(page_number)

    def break_document_into_chapters(
        self,
        ChapterDerived: type[TopLevelChapter] = None,
    ) -> None:
        current_chapter = None
        # The page number of the page that opened the current chapter (the
        # page layout of a chapter is only known once its first page is added)
        current_chapter_page_number = None
        for page_number in range(0, self.structural_info.total_page_number):

            if self.structural_info._page_is_dropped(page_number):
                continue

            ### Create a new extracted page:
            new_extracted_page_layout = PageLayout(
                self.structural_info.convert_to_logical_page_number(page_number),
                page_number,
            )
            new_extracted_page = ExtractedPage(
                page_number,
                new_extracted_page_layout,
                self.reader.pages[page_number],  # Original page
            )
            new_extracted_page.set_text(self.extracted_texts[page_number])
            new_extracted_page.removed_first_line_indentation = (
                self.removed_first_line_indentations.get(page_number, 0)
            )

            if not self.chapter_splitter.holds_new_chapter(new_extracted_page):
                # When the new extracted page is not the beginning of a chapter
                # we must still assert that the current_chapter was previously
                # encountered
                if not current_chapter:
                    # We didn't encounter a first chapter yet the first
                    # encountered page is not a page starting a chapter.
                    # Something went really wrong.
                    raise ConverterError(
                        f"Any chapter must start with...a chapter typed page.\nNote: we didn't encounter the first chapter yet.\nThis was the content of the extracted page: {new_extracted_page}"
                    )
            else:
                # This new extracted page is the one of a new chapter. We must
                # thus create it (a Chapter object) as such and define this new
                # Chapter as the current_chapter:
                new_chapter_name = self.chapter_splitter.get_chapter_name(
                    new_extracted_page
                )
                if new_chapter_name is None:
                    raise ConverterError(
                        f"This looks like a new chapter yet it has no name.\nThis was the content of the extracted page: {new_extracted_page}"
                    )

                sanitized_new_chapter_name = TextSanitizer.normalize_chapter_name(
                    new_chapter_name, self.structural_info.character_folding_rules()
                )
                current_chapter = ChapterDerived(sanitized_new_chapter_name)
                current_chapter_page_number = new_extracted_page.page_number
                self.document.add_chapter(current_chapter)
                # Remove chapter name from page text
                self.chapter_splitter.extract_chapter_name(
                    new_extracted_page, new_chapter_name
                )
                # The first line of the page text is not the first line of the
                # page anymore.
                new_extracted_page.removed_first_line_indentation = 0

            # We are back to the default flow of treatment
            # The page knows its chapter before its text is treated (the
            # sanitizing of a book may depend on it, e.g. to expect the header
            # of the page)
            new_extracted_page.chapter_name = current_chapter.name
            new_extracted_page.chapter_page_number = current_chapter_page_number
            # The tables are cut out first: the sanitizing and the typo fixing
            # of the book are meant for running text.
            self.table_extractor.extract_tables(new_extracted_page)
            self.structural_info.sanitize_page_text(new_extracted_page)
            typo_fixes = self.structural_info.page_info(
                new_extracted_page.page_number
            ).typo_fixes
            self.typo_fixer.fix(new_extracted_page, typo_fixes)
            current_chapter.add_page(new_extracted_page)
        self.table_extractor.check_all_tables_closed()

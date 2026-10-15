from .ConverterConfig import ConverterConfig
from .DiagnosticsReporter import DiagnosticsReporter
from .Errors import ConverterError
from .Model import TopLevelChapter
from .DocumentBuilder import DocumentBuilder
from .DocumentBreaker import DocumentBreaker


class ConverterBase(DocumentBuilder):
    """
    Class converting the original set of pages extracted from the pypdf::reader
    to a structured document. In order to realize its purpose the Converter
    needs to be manually provided with the structural information (extracted by
    a human reader) that must be promoted to the semantic structure (document,
    chapter, sub-chapter, paragraph...).
    """

    def __init__(self, pdf_filename, document, structural_info, config: ConverterConfig | None = None) -> None:
        self.pdf_filename = pdf_filename
        diagnostics = DiagnosticsReporter(
            config.warning_mode if config is not None else False,
            config.debug_mode if config is not None else False,
        )
        structural_info.set_diagnostics(diagnostics)
        DocumentBuilder.__init__(self, document, structural_info, diagnostics)
        self.build_document()

    def get_chapter_extracted_page(self, extracted_page):
        """Get the extracted page of the chapter holding the given extracted page."""
        chapter_page_number = self.structural_info._get_chapter_page_number(
            extracted_page.page_number
        )
        chapter_extracted_page = self.document.get_chapter_extracted_page(
            chapter_page_number
        )
        if not chapter_extracted_page:
            raise ConverterError(
                f"Chapter for page number {extracted_page.page_number} not found."
            )
        return chapter_extracted_page

    def break_document_into_chapters(
        self,
        ChapterDerived: type[TopLevelChapter] = None,
    ) -> None:
        document_breaker = DocumentBreaker(
            self.pdf_filename,
            self.document,
            self.structural_info,
            diagnostics=self._diagnostics,
        )
        document_breaker.break_document_into_chapters(ChapterDerived)

    def get_document(self):
        return self.document

from .DiagnosticsReporter import DiagnosticsReporter
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

    def __init__(
        self, pdf_filename, document, structural_info, maximum_line_length=None
    ) -> None:
        self.pdf_filename = pdf_filename
        diagnostics = DiagnosticsReporter()
        structural_info.set_diagnostics(diagnostics)
        document.numbered_list_heuristics_enabled = (
            structural_info.numbered_list_heuristics_enabled
        )
        # See LineWrapper (None: the lines of the paragraphs are never broken)
        document.maximum_line_length = maximum_line_length
        DocumentBuilder.__init__(self, document, structural_info, diagnostics)
        self.build_document()

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

"""Minimal concrete StructuralInfoBase and ConverterBase subclasses for tests."""

from pdf_to_markdown import (
    ConverterBase,
    Document,
    NameLessSinglePatternSplitter,
    StructuralInfoBase,
    TopLevelChapterOfParagraphs,
)


class FixtureStructuralInfo(StructuralInfoBase):
    """4-page fixture: pages 0 and 2 are chapter headings; 1 and 3 are body."""

    class chapter_splitter:
        """Simple splitter that relies entirely on static pages_info declarations."""

        def __init__(self, structural_info):
            self._structural_info = structural_info

        def holds_new_chapter(self, extracted_page) -> bool:
            return self._structural_info._holds_new_chapter(extracted_page.page_number)

        def get_chapter_name(self, extracted_page):
            return self._structural_info._get_chapter_name(extracted_page.page_number)

        def extract_chapter_name(self, extracted_page, chapter_name):
            # Strip the chapter heading characters from the page text so the
            # chapter page contributes no body-paragraph content.
            extracted_page.text = extracted_page.text.lstrip(chapter_name)

    @property
    def pages_info(self) -> dict:
        return {
            0: {"type": "chapter", "chapter_info": {"name": "Chapter One"}},
            2: {"type": "chapter", "chapter_info": {"name": "Chapter Two"}},
        }

    @property
    def total_page_number(self) -> int:
        return 4

    def chapter_to_paragraph_splitter(self):
        # Pattern "\n    " (newline + 4 spaces) marks paragraph boundaries in
        # the real books; the fixture body text never contains this sequence,
        # so each page becomes a single unbroken paragraph.
        return NameLessSinglePatternSplitter(r"\n    ")


class FixtureConverter(ConverterBase):
    """Concrete converter for the 4-page fixture PDF."""

    def break_document_into_chapters(self):
        # ConverterBase.break_document_into_chapters requires the concrete
        # chapter class to instantiate; pass TopLevelChapterOfParagraphs
        # because the fixture uses a flat Document (no SuperChapter).
        ConverterBase.break_document_into_chapters(self, TopLevelChapterOfParagraphs)


def build_fixture_document(pdf_path: str) -> Document:
    """Run the full pipeline on the fixture PDF and return the Document."""
    document = Document("Fixture Document")
    structural_info = FixtureStructuralInfo()
    FixtureConverter(pdf_path, document, structural_info)
    return document

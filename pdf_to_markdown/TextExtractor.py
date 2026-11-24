class TextExtractor:
    """
    Pre-extracts text from all PDF pages before chapter breaking begins.
    This separates the text extraction concern from DocumentBreaker.
    """

    def __init__(self, reader, structural_info) -> None:
        self.reader = reader
        self.structural_info = structural_info
        # For each page, the number of whitespaces that were removed from the
        # indentation of its first line (see ExtractedPage).
        self.removed_first_line_indentations: dict[int, int] = {}

    @staticmethod
    def _first_line_indentation(text: str) -> int:
        for line in text.split("\n"):
            if line.strip():
                return len(line) - len(line.lstrip(" "))
        return 0

    def extract_all(self) -> dict[int, str]:
        """
        Extract text from all pages.
        Returns a dict mapping page_number to extracted text.
        """
        extracted_texts = {}
        for page_number in range(self.structural_info.total_page_number):
            if self.structural_info._page_is_dropped(page_number):
                continue
            original_page = self.reader.pages[page_number]
            try:
                text = original_page.extract_text(extraction_mode="layout")
            except NotImplementedError:
                # Fallback for PDFs with filter arrays that pypdf can't handle
                # in layout mode
                text = original_page.extract_text()
            # Normalize tabs to spaces (some PDFs have tabs instead of spaces)
            text = text.replace("\t", " ")
            # lstrip is required before holds_new_chapter classification
            # It is delegated to the structural info because a book might
            # have to keep the indentation of the first line of a page (e.g.
            # a blockquote starting at the very top of a page).
            extracted_texts[page_number] = (
                self.structural_info.strip_page_text_leading_whitespace(text)
            )
            self.removed_first_line_indentations[page_number] = max(
                0,
                self._first_line_indentation(text)
                - self._first_line_indentation(extracted_texts[page_number]),
            )
        return extracted_texts

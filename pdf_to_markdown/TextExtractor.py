from .TextSanitizer import TextSanitizer


class TextExtractor:
    """
    Pre-extracts text from all PDF pages before chapter breaking begins.
    This separates the text extraction concern from DocumentBreaker.

    The text that comes out is plain ASCII (see TextSanitizer.sanitize_characters
    and TextSanitizer.normalize_spaced_ellipsis): this is the only place where
    the text of the pages is folded. Whatever reads it downstream (the regexes
    of a StructuralInfo, the sanitizing of a book, the typos to fix...) is thus
    written against ASCII text, and nothing needs to fold the text again.

    Mind that some characters fold to several ASCII characters: an em dash
    becomes "--", an ellipsis "...", a smiling face ":-)". A regex that
    stood for such a character with a single wildcard (".") has to spell what
    it folds to.
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
            # Fold to ASCII (typographic quotes and dashes, diacritics...) and
            # spell the ellipses the one way that keeps them within their
            # sentence (". . ." would be cut into one sentence per dot by the
            # sentence tokenizer), see the class documentation.
            text = TextSanitizer.sanitize_characters(text)
            text = TextSanitizer.normalize_spaced_ellipsis(text)
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

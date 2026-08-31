import re


class TextSanitizer:
    """Text sanitization utilities for extracted PDF content."""

    @staticmethod
    def _normalize_typographic_quotes(text: str) -> str:
        """Replace typographic (curly) single quote characters with ASCII equivalents.

        U+2018 LEFT SINGLE QUOTATION MARK is used exclusively as an opening
        quotation mark and never as an apostrophe within a word. It is
        therefore removed entirely.

        U+2019 RIGHT SINGLE QUOTATION MARK serves two distinct roles: as a
        closing quotation mark and as an apostrophe within contractions
        (e.g. don't) and possessives (e.g. monk's). It is normalized to an
        ASCII apostrophe so that those uses are preserved.
        """
        # U+2018 is always an opening quotation mark, never an apostrophe:
        # remove it entirely.
        text = text.replace(
            "‘",  # LEFT SINGLE QUOTATION MARK
            "",
        )
        # U+2019 followed by whitespace is a closing quotation mark, not an apostrophe:
        # remove it (the whitespace is preserved via lookahead).
        text = re.sub("’(?=\\s)", "", text)
        # U+2019 not followed by whitespace is an apostrophe in a contraction or possessive:
        # normalize to ASCII apostrophe.
        text = text.replace(
            "’",  # RIGHT SINGLE QUOTATION MARK
            "'",       # ASCII APOSTROPHE (U+0027)
        )
        return text

    def sanitize_newlines_and_multiple_whitespaces(self, input_text: str) -> str:
        """Remove newlines and collapse multiple whitespaces.

        Newlines are encountered to denote different usages:
        - set some tabulations of illuminations (example "\\       ")
        - define a new paragraph in which case newline is followed by
          exactly 4 whitespaces (example "\\n    "): refer to
          break_chapter_into_paragraphs() method
        - simple line folding within original paragraphs or even sentences
          where newlines are used to format the original pdf with line returns.
        """
        input_text = self._normalize_typographic_quotes(input_text)
        input_text = input_text.replace("\n", " ")
        return re.sub(r"\s+", " ", input_text).strip()

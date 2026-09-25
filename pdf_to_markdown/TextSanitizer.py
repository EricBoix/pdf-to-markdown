import re


class TextSanitizer:
    """Text sanitization utilities for extracted PDF content."""

    @staticmethod
    def _normalize_typographic_quotes(text: str) -> str:
        """ASCII fold typographic (curly) quote characters (single and double).

        Single quotes: U+2018 LEFT SINGLE QUOTATION MARK and U+2019 RIGHT SINGLE
        QUOTATION MARK are folded to U+0027 ASCII APOSTROPHE.
        Note: U+2019 serves distinct roles (closing quotation mark, contraction
        apostrophe e.g. don't, possessive e.g. monk's); the folding is
        many-to-one.

        Double quotes: U+201C LEFT DOUBLE QUOTATION MARK and U+201D RIGHT DOUBLE
        QUOTATION MARK are folded to U+0022 ASCII QUOTATION MARK.
        """
        # fmt: off
        text = text.replace(
            "\u2018",  # U+2018 LEFT SINGLE QUOTATION MARK
            "\u0027",  # U+0027 ASCII APOSTROPHE
        )
        text = text.replace(
            "\u2019",  # U+2019 RIGHT SINGLE QUOTATION MARK
            "\u0027",  # U+0027 ASCII APOSTROPHE
        )
        text = text.replace(
            "\u201c",  # U+201C LEFT DOUBLE QUOTATION MARK
            "\u0022",  # U+0022 ASCII QUOTATION MARK
        )
        text = text.replace(
            "\u201d",  # U+201D RIGHT DOUBLE QUOTATION MARK
            "\u0022",  # U+0022 ASCII QUOTATION MARK
        )
        # fmt: on
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

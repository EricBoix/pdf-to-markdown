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

    @staticmethod
    def _normalize_diacritics(text: str) -> str:
        """ASCII fold Pali diacritic characters to their base ASCII equivalents.

        Pali transliteration uses several extended Latin characters that have no
        ASCII counterpart. Each is folded to the closest ASCII base letter.
        """
        # fmt: off
        text = text.replace(
            "\u00f1",  # U+00F1 LATIN SMALL LETTER N WITH TILDE
            "n",       # U+006E ASCII LATIN SMALL LETTER N
        )
        text = text.replace(
            "\u0101",  # U+0101 LATIN SMALL LETTER A WITH MACRON
            "a",       # U+0061 ASCII LATIN SMALL LETTER A
        )
        text = text.replace(
            "\u012b",  # U+012B LATIN SMALL LETTER I WITH MACRON
            "i",       # U+0069 ASCII LATIN SMALL LETTER I
        )
        text = text.replace(
            "\u1e37",  # U+1E37 LATIN SMALL LETTER L WITH DOT BELOW
            "l",       # U+006C ASCII LATIN SMALL LETTER L
        )
        text = text.replace(
            "\u1e43",  # U+1E43 LATIN SMALL LETTER M WITH DOT BELOW
            "m",       # U+006D ASCII LATIN SMALL LETTER M
        )
        text = text.replace(
            "\u1e47",  # U+1E47 LATIN SMALL LETTER N WITH DOT BELOW
            "n",       # U+006E ASCII LATIN SMALL LETTER N
        )
        text = text.replace(
            "\u1e6d",  # U+1E6D LATIN SMALL LETTER T WITH DOT BELOW
            "t",       # U+0074 ASCII LATIN SMALL LETTER T
        )
        # fmt: on
        return text

    @staticmethod
    def _normalize_dashes(text: str) -> str:
        """ASCII fold typographic dash characters.

        U+2014 EM DASH is folded to -- (two ASCII hyphens), the established
        plain-text convention for an em dash.
        U+2013 EN DASH is folded to - (one ASCII hyphen), used for numeric ranges.
        """
        # fmt: off
        text = text.replace(
            "\u2014",  # U+2014 EM DASH
            "--",      # two ASCII hyphens
        )
        text = text.replace(
            "\u2013",  # U+2013 EN DASH
            "-",       # U+002D ASCII HYPHEN-MINUS
        )
        # fmt: on
        return text

    def _normalize_newlines_and_multiple_whitespaces(self, input_text: str) -> str:
        """Remove newlines and collapse multiple whitespaces.

        Newlines are encountered to denote different usages:
        - set some tabulations of illuminations (example "\\       ")
        - define a new paragraph in which case newline is followed by
          exactly 4 whitespaces (example "\\n    "): refer to
          break_chapter_into_paragraphs() method
        - simple line folding within original paragraphs or even sentences
          where newlines are used to format the original pdf with line returns.
        """
        input_text = input_text.replace("\n", " ")
        return re.sub(r"\s+", " ", input_text).strip()

    @staticmethod
    def sanitize_characters(input_text: str) -> str:
        """ASCII-fold all known non-ASCII characters (quotes, diacritics, dashes)."""
        input_text = TextSanitizer._normalize_typographic_quotes(input_text)
        input_text = TextSanitizer._normalize_diacritics(input_text)
        input_text = TextSanitizer._normalize_dashes(input_text)
        return input_text

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
        """ASCII fold typographic dash and ellipsis characters.

        U+2014 EM DASH is folded to -- (two ASCII hyphens), the established
        plain-text convention for an em dash.
        U+2013 EN DASH is folded to - (one ASCII hyphen), used for numeric ranges.
        U+2026 HORIZONTAL ELLIPSIS is folded to ... (three ASCII full stops).
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
        text = text.replace(
            "\u2026",  # U+2026 HORIZONTAL ELLIPSIS
            "...",     # three ASCII full stops
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
    def _normalize_symbols(text: str) -> str:
        """ASCII fold miscellaneous symbol characters.

        U+263A WHITE SMILING FACE and U+F04A (private-use smiling face glyph
        found in some PDF fonts) are both folded to the ASCII emoticon :-).
        """
        # fmt: off
        text = text.replace(
            "\u263a",  # U+263A WHITE SMILING FACE
            ":-)",      # ASCII emoticon
        )
        text = text.replace(
            "\uf04a",  # U+F04A private-use smiling face (PDF font glyph)
            ":-)",      # ASCII emoticon
        )
        # fmt: on
        return text

    @staticmethod
    def normalize_chapter_name(raw_name: str) -> str:
        """Collapse newlines and ASCII-fold a raw chapter or sub-chapter name.

        A newline flanked on both sides by an uppercase letter is a within-word
        PDF renderer split (e.g. "GET\\nTING"); it is removed rather than
        replaced with a space.  All other newlines denote line breaks between
        words and are replaced with a space.  sanitize_characters() is then
        applied to fold any remaining non-ASCII characters.
        """
        name = re.sub(r"([A-Z])\n([A-Z])", r"\1\2", raw_name)
        name = name.replace("\n", " ")
        return TextSanitizer.sanitize_characters(name)

    @staticmethod
    def sanitize_characters(input_text: str) -> str:
        """ASCII-fold all known non-ASCII characters (quotes, diacritics, dashes, symbols)."""
        input_text = TextSanitizer._normalize_typographic_quotes(input_text)
        input_text = TextSanitizer._normalize_diacritics(input_text)
        input_text = TextSanitizer._normalize_dashes(input_text)
        input_text = TextSanitizer._normalize_symbols(input_text)
        return input_text

    _MISMATCH_START = "<<PDF_TO_MARKDOWN DETECTED MISSMATCH: START>>"
    _MISMATCH_END = "<<PDF_TO_MARKDOWN DETECTED MISSMATCH: END>>"

    @staticmethod
    def _has_word_terminal_apostrophe(sentence: str) -> bool:
        """True when the sentence starts with ' and has an unmatched word-terminal apostrophe.

        A word-terminal apostrophe (letter before, space after) creates genuine
        ambiguity only when the sentence itself starts with ': that opening '
        might be a paragraph-opening quote, making it unclear whether the
        word-terminal ' later in the sentence closes it or is simply possessive.

        If the sentence does not start with ', a word-terminal ' can only be
        possessive (e.g. James' in an attribution sentence), so no ambiguity
        arises and the function returns False.

        A word-terminal ' that has an inner-sentence word-initial partner
        (a ' preceded by whitespace or punctuation, like 'homeless in
        'homeless monk') is considered balanced and does not trigger framing.

        When no inner-sentence partner exists, the sentence-opening ' at
        position 0 is also treated as a valid partner when the tail text after
        the word-terminal ' spans at least two words, which is characteristic
        of an attribution phrase (e.g. "'You are dead all right' observed the
        teacher."). A single-word tail (e.g. "cat." in "'John saw James' cat.")
        cannot be attribution, so the word-terminal ' remains ambiguous and
        triggers framing.
        """
        if not sentence.startswith("'"):
            return False
        word_terminals = [
            m.start() for m in re.finditer(r"(?<=[A-Za-z])'(?=\s)", sentence)
        ]
        if not word_terminals:
            return False
        inner_initials = [
            m.start() for m in re.finditer(r"(?<=[\s,;:])'(?=[A-Za-z])", sentence)
        ]
        return any(
            not any(init < terminal for init in inner_initials)
            and len(sentence[terminal + 1 :].split()) < 2
            for terminal in word_terminals
        )

    @staticmethod
    def _frame_sentence_if_unbalanced(sentence: str) -> str:
        """Frame a sentence that contains a word-terminal apostrophe.

        A word-terminal apostrophe (letter before, space after) is genuinely
        ambiguous: it could be a possessive or a closing quotation mark.  Rather
        than guessing, the sentence is wrapped in mismatch markers so the problem
        is visible in the final output.

        All other sentences — including NLTK-split fragments whose boundary ' has
        no matching partner — are returned unchanged.
        """
        if TextSanitizer._has_word_terminal_apostrophe(sentence):
            return (
                TextSanitizer._MISMATCH_START + sentence + TextSanitizer._MISMATCH_END
            )
        return sentence

    @staticmethod
    def split_paragraph_respecting_quotes(
        paragraph_text: str, sanitized_sentences: list[str]
    ) -> list[str]:
        """Pass sentences through, framing any that contain a word-terminal apostrophe.

        NLTK-split fragments from singly-quoted paragraphs (e.g. 'It is overfull.
        or No more will go in!') are returned unchanged — their boundary apostrophes
        are unambiguous artifacts of the split and do not need correction.

        Sentences with a word-terminal apostrophe (letter before, space after, e.g.
        James' in "'John saw James' cat.") are wrapped in mismatch markers because
        it is impossible to tell automatically whether the apostrophe is possessive
        or a closing quotation mark.
        """
        return [
            TextSanitizer._frame_sentence_if_unbalanced(sentence)
            for sentence in sanitized_sentences
        ]

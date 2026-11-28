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

    @staticmethod
    def normalize_newlines_and_multiple_whitespaces(input_text: str) -> str:
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
    def normalize_chapter_name(raw_name: str, folding_rules=()) -> str:
        """Collapse newlines and ASCII-fold a raw chapter or sub-chapter name.

        A newline flanked on both sides by an uppercase letter is a within-word
        PDF renderer split (e.g. "GET\\nTING"); it is removed rather than
        replaced with a space.  All other newlines denote line breaks between
        words and are replaced with a space.  sanitize_characters() is then
        applied to fold any remaining non-ASCII characters.
        """
        # The right-hand side must continue with a second uppercase letter,
        # otherwise a capitalized word starting a new line (e.g.
        # "INTERLUDE\nConscious") would wrongly be glued to the previous word.
        name = re.sub(r"([A-Z])\n([A-Z])(?=[A-Z])", r"\1\2", raw_name)
        name = name.replace("\n", " ")
        return TextSanitizer.sanitize_characters(name, folding_rules)

    @staticmethod
    def sanitize_characters(input_text: str, folding_rules=()) -> str:
        """ASCII-fold the typographic quotes and dashes (a fact, see
        docs/rules_implicit.md), then the characters of the given rules (see
        TypoRuleForCharacters: diacritics, symbols...), that a document holds
        or not."""
        input_text = TextSanitizer._normalize_typographic_quotes(input_text)
        input_text = TextSanitizer._normalize_dashes(input_text)
        for folding_rule in folding_rules:
            input_text = folding_rule.fold(input_text)
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
    def frame_sentences_if_unbalanced(sanitized_sentences: list[str]) -> list[str]:
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

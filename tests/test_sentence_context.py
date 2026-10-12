"""Tests for the sentence-level pipeline stages.

Two distinct contexts live here:
  - Character sanitization: folding of non-ASCII chars in sentence text.
  - Sentence splitting: boundary-apostrophe handling aware of whole-paragraph
    quoting (TextSanitizer.split_paragraph_respecting_quotes).

Examples for each context are imported from fixtures/text_examples.py to
prevent accidental cross-stage mixing.
"""

import pytest

from pdf_to_markdown import TextSanitizer

from .fixtures.text_examples import SENTENCE_CHARACTER_EXAMPLES, SENTENCE_SPLIT_EXAMPLES


class TestCharacterSanitization:
    """TextSanitizer.sanitize_characters applied at the sentence level."""

    @pytest.mark.parametrize("input_text,expected", SENTENCE_CHARACTER_EXAMPLES)
    def test_sanitize_characters(self, input_text, expected):
        assert TextSanitizer.sanitize_characters(input_text) == expected

    def test_sanitize_characters_is_idempotent(self):
        # Applying sanitization twice produces the same result as once.
        source = "don’t end… a—b"
        once = TextSanitizer.sanitize_characters(source)
        twice = TextSanitizer.sanitize_characters(once)
        assert once == twice


class TestSentenceSplitting:
    """TextSanitizer.split_paragraph_respecting_quotes."""

    @pytest.mark.parametrize(
        "paragraph_text,sanitized_sentences,expected",
        SENTENCE_SPLIT_EXAMPLES,
    )
    def test_split_paragraph_respecting_quotes(
        self, paragraph_text, sanitized_sentences, expected
    ):
        result = TextSanitizer.split_paragraph_respecting_quotes(
            paragraph_text, sanitized_sentences
        )
        assert result == expected

    def test_typographic_quotes_detected_as_quoted_paragraph(self):
        # Typographic quotes are folded before the whole-paragraph detection,
        # so a paragraph wrapped in U+2018/U+2019 is treated as quoted.
        # paragraph_text carries the original typographic quotes; the
        # sanitized_sentences already have them folded to ASCII apostrophes
        # (as DocumentBuilder does before calling this method).
        # Use explicit codepoints to prevent editor auto-conversion.
        apos = chr(0x0027)  # U+0027 ASCII APOSTROPHE
        lsqm = chr(0x2018)  # U+2018 LEFT SINGLE QUOTATION MARK
        rsqm = chr(0x2019)  # U+2019 RIGHT SINGLE QUOTATION MARK
        paragraph_text = lsqm + "It is overfull. No more will go in!" + rsqm
        sanitized_sentences = [
            apos + "It is overfull.",
            "No more will go in!" + apos,
        ]
        result = TextSanitizer.split_paragraph_respecting_quotes(
            paragraph_text, sanitized_sentences
        )
        assert result == [
            apos + "It is overfull." + apos,
            apos + "No more will go in!" + apos,
        ]

    def test_empty_sentence_list_returns_empty(self):
        result = TextSanitizer.split_paragraph_respecting_quotes("Any text.", [])
        assert result == []

"""Tests for the sentence-level pipeline stages.

Two distinct contexts live here:
  - Character sanitization: folding of non-ASCII chars in sentence text.
  - Sentence splitting: boundary apostrophes are re-wrapped when unbalanced
    (TextSanitizer.split_paragraph_respecting_quotes, odd-count rule).

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
        "paragraph_text,sanitized_sentences,expected_sentences",
        SENTENCE_SPLIT_EXAMPLES,
    )
    def test_split_paragraph_rewraps_unbalanced_quotes(
        self, paragraph_text, sanitized_sentences, expected_sentences
    ):
        result = TextSanitizer.split_paragraph_respecting_quotes(
            paragraph_text, sanitized_sentences
        )
        assert result == expected_sentences

    def test_empty_sentence_list_returns_empty(self):
        result = TextSanitizer.split_paragraph_respecting_quotes("Any text.", [])
        assert result == []

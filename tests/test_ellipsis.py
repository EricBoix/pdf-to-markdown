"""A spaced ellipsis (". . .") is turned into a plain one that stays inside its sentence."""

import nltk
import pytest

from pdf_to_markdown import PageLayout, Sentence, TextSanitizer


class TestNormalizeSpacedEllipsis:
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("there is . . .", "there is..."),
            ("Fine . . . Next one starts here.", "Fine... Next one starts here."),
            ("no space before. . . and after", "no space before... and after"),
            ("A plain ellipsis... stays", "A plain ellipsis... stays"),
            ("Nothing to change.", "Nothing to change."),
        ],
    )
    def test_normalize_spaced_ellipsis(self, input_text, expected):
        assert TextSanitizer.normalize_spaced_ellipsis(input_text) == expected

    def test_normalize_spaced_ellipsis_is_idempotent(self):
        once = TextSanitizer.normalize_spaced_ellipsis("there is . . .")
        assert TextSanitizer.normalize_spaced_ellipsis(once) == once


class TestEllipsisWithinSentences:
    def test_ellipsis_does_not_cut_the_sentence(self):
        text = TextSanitizer.normalize_spaced_ellipsis(
            "It ends. When the mind is unified, there is . . ."
        )
        assert nltk.tokenize.sent_tokenize(text) == [
            "It ends.",
            "When the mind is unified, there is...",
        ]

    def test_sentence_ending_with_an_ellipsis_is_complete(self):
        assert Sentence("The mind is there...", PageLayout(1, 1)).is_complete()

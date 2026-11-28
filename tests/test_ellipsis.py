"""A spaced ellipsis (". . .") is turned into a plain one that stays inside its sentence."""

import nltk
import pytest

from pdf_to_markdown.typo_rules import SpacedEllipsisIsAnEllipsis


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
        assert SpacedEllipsisIsAnEllipsis().normalize(input_text) == expected

    def test_normalize_spaced_ellipsis_is_idempotent(self):
        rule = SpacedEllipsisIsAnEllipsis()
        once = rule.normalize("there is . . .")
        assert rule.normalize(once) == once

    def test_substitutions_are_counted(self):
        rule = SpacedEllipsisIsAnEllipsis()
        assert rule.substitution_count("a . . . b. . . c... d") == 2


class TestEllipsisWithinSentences:
    def test_ellipsis_does_not_cut_the_sentence(self):
        text = SpacedEllipsisIsAnEllipsis().normalize(
            "It ends. When the mind is unified, there is . . ."
        )
        assert nltk.tokenize.sent_tokenize(text) == [
            "It ends.",
            "When the mind is unified, there is...",
        ]

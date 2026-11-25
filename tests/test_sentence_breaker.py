"""SentenceBreaker cuts the (ASCII) text of a paragraph into sentences, from text only.

The folding to ASCII and the spelling of the ellipses are done once for all
when the text is extracted, see test_text_extractor.py."""

import pytest

from pdf_to_markdown import SentenceBreaker, TextSanitizer


class TestBreakIntoSentences:
    def test_text_is_cut_at_the_end_of_its_sentences(self):
        assert SentenceBreaker.break_into_sentences(
            "The mind is calm. Awareness is clear!"
        ) == ["The mind is calm.", "Awareness is clear!"]

    def test_plain_ellipsis_stays_within_its_sentence(self):
        assert SentenceBreaker.break_into_sentences(
            "It ends. When the mind is unified, there is..."
        ) == ["It ends.", "When the mind is unified, there is..."]

    def test_boundary_apostrophes_of_a_quotation_are_preserved(self):
        assert SentenceBreaker.break_into_sentences(
            "'It is overfull. No more will go in!'"
        ) == ["'It is overfull.", "No more will go in!'"]

    def test_newlines_and_multiple_whitespaces_are_collapsed(self):
        assert SentenceBreaker.break_into_sentences(
            "The line\nis cut   in\n    two.  Next one."
        ) == ["The line is cut in two.", "Next one."]

    def test_sentence_with_an_ambiguous_apostrophe_is_framed(self):
        assert SentenceBreaker.break_into_sentences("'John saw James' cat.") == [
            TextSanitizer._MISMATCH_START
            + "'John saw James' cat."
            + TextSanitizer._MISMATCH_END
        ]

    @pytest.mark.parametrize("text", ["", "   ", "\n\n"])
    def test_text_without_sentence_gives_no_sentence(self, text):
        assert SentenceBreaker.break_into_sentences(text) == []

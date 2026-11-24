"""Tests for the breaking of the long lines of a paragraph.

Lines are only separated by a single newline: a blank line would start a new
paragraph.
"""

from pdf_to_markdown import LineWrapper

TEXT = "one two three four five six seven eight nine ten"


class TestLineWrapper:
    def test_no_limit_leaves_text_unchanged(self):
        assert LineWrapper.wrap(TEXT, None) == TEXT
        assert LineWrapper.wrap(TEXT, 0) == TEXT

    def test_short_text_is_unchanged(self):
        assert LineWrapper.wrap(TEXT, 1000) == TEXT

    def test_lines_respect_the_limit_and_no_blank_line_appears(self):
        wrapped = LineWrapper.wrap(TEXT, 15)
        lines = wrapped.split("\n")
        assert all(len(line) <= 15 for line in lines)
        assert all(line != "" for line in lines)
        assert " ".join(lines) == TEXT

    def test_overlong_word_is_left_unbroken(self):
        assert LineWrapper.wrap("a b supercalifragilistic c", 8) == (
            "a b\nsupercalifragilistic\nc"
        )

    def test_list_continuation_lines_keep_the_indentation(self):
        text = "   " + TEXT
        lines = LineWrapper.wrap(text, 18, "   ").split("\n")
        assert all(line.startswith("   ") for line in lines)
        assert all(len(line) <= 18 for line in lines)
        assert " ".join(line.strip() for line in lines) == TEXT

    def test_blockquote_continuation_lines_keep_the_marker(self):
        text = "> " + TEXT
        lines = LineWrapper.wrap(text, 16, "> ").split("\n")
        assert all(line.startswith("> ") for line in lines)
        assert all(len(line) <= 16 for line in lines)
        assert " ".join(line[2:] for line in lines) == TEXT

    def test_a_line_never_starts_with_a_block_opening_word(self):
        text = "aaaa bbbb 2. cccc - dddd # eeee > ffff"
        for line in LineWrapper.wrap(text, 9).split("\n"):
            assert line.split(" ")[0] not in ("2.", "-", "#", ">")


class TestLineWrapperBySentences:
    SENTENCES = ["First one here.", "Second one there.", "Third.", "Fourth is last."]

    def test_no_limit_gives_one_line(self):
        assert LineWrapper.wrap_sentences(self.SENTENCES, None) == " ".join(
            self.SENTENCES
        )

    def test_lines_end_at_the_end_of_sentences(self):
        lines = LineWrapper.wrap_sentences(self.SENTENCES, 35).split("\n")
        assert lines == [
            "First one here. Second one there.",
            "Third. Fourth is last.",
        ]

    def test_prefix_counts_and_starts_every_line(self):
        lines = LineWrapper.wrap_sentences(self.SENTENCES, 38, "> ").split("\n")
        assert all(line.startswith("> ") and len(line) <= 38 for line in lines)
        assert " ".join(line[2:] for line in lines) == " ".join(self.SENTENCES)

    def test_overlong_sentence_is_broken_between_words(self):
        sentences = ["Short.", "one two three four five six seven", "End."]
        lines = LineWrapper.wrap_sentences(sentences, 15).split("\n")
        assert all(len(line) <= 15 for line in lines)
        assert " ".join(lines) == " ".join(sentences)

    def test_suffix_is_appended_to_the_last_line(self):
        wrapped = LineWrapper.wrap_sentences(self.SENTENCES, 35, "", " <!-- n -->")
        assert wrapped.endswith("Fourth is last. <!-- n -->")

    def test_suffix_counts_in_the_line_length_and_is_never_broken(self):
        note = " <!-- a note -->"
        lines = LineWrapper.wrap_sentences(self.SENTENCES, 35, "", note).split("\n")
        assert all(len(line) <= 35 for line in lines)
        assert lines[-1].endswith("last." + note)

    def test_no_break_inside_an_open_double_quote(self):
        quotation = [
            "Questions may arise such as, \"What does 'pushy' mean?",
            '", "Should I feel ashamed?',
            '", or "Is it true?" and "Should I try?"',
        ]
        sentences = ["Opening sentence of the paragraph."] + quotation + ["Next one."]
        # The limit only allows the opening sentence alone on the first line
        # and the whole quotation on the second one.
        lines = LineWrapper.wrap_sentences(sentences, 140).split("\n")
        assert lines[0] == "Opening sentence of the paragraph."
        assert lines[1].startswith(" ".join(quotation))

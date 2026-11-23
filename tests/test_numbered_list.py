"""Tests for the numbered lists spread over the paragraphs of a level.

Once converted to markdown, the paragraphs separating the items of a numbered
list must be indented (otherwise the list is broken in several lists that do
not start at one, which markdownlint rule MD029 rejects), and a paragraph that
only looks like an item must not start a list.
"""

from pdf_to_markdown import (
    NumberedListAnnotator,
    NumberedListRole,
)

NONE = NumberedListRole.NONE
CONTINUATION = NumberedListRole.CONTINUATION
ESCAPED_ITEM = NumberedListRole.ESCAPED_ITEM


class TestNumberedListAnnotator:
    def test_consecutive_items_need_no_change(self):
        texts = ["1. First", "2. Second", "3. Third"]
        assert NumberedListAnnotator().annotate(texts) == [NONE, NONE, NONE]

    def test_paragraphs_between_items_are_continuations(self):
        texts = ["1. Posture", "a. Sit.", "b. Straighten.", "2. Relax", "Done."]
        assert NumberedListAnnotator().annotate(texts) == [
            NONE,
            CONTINUATION,
            CONTINUATION,
            NONE,
            NONE,
        ]

    def test_item_of_a_list_that_never_started_is_escaped(self):
        texts = ["Some text.", "2. Set goals", "More text.", "5. Review"]
        assert NumberedListAnnotator().annotate(texts) == [
            NONE,
            ESCAPED_ITEM,
            NONE,
            ESCAPED_ITEM,
        ]

    def test_sibling_that_is_not_a_paragraph_ends_the_list(self):
        texts = ["1. First", None, "2. Second"]
        assert NumberedListAnnotator().annotate(texts) == [NONE, NONE, ESCAPED_ITEM]

    def test_next_item_too_far_away_is_not_a_continuation(self):
        distance = NumberedListAnnotator.MAX_PARAGRAPHS_BETWEEN_ITEMS
        texts = ["1. First"] + ["Text."] * (distance + 1) + ["2. Second"]
        roles = NumberedListAnnotator().annotate(texts)
        assert set(roles[1:-1]) == {NONE}

    def test_item_text_helpers(self):
        assert NumberedListAnnotator.escape_item("2. Relax") == "2\\. Relax"
        assert NumberedListAnnotator.indent_continuation("a. Sit") == "   a. Sit"

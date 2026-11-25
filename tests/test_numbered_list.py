"""Tests for the numbered lists spread over the paragraphs of a level.

Once converted to markdown, the paragraphs separating the items of a numbered
list must be indented (otherwise the list is broken in several lists that do
not start at one, which markdownlint rule MD029 rejects), a paragraph that
only looks like an item is left untouched and a numbering that restarts at
one while a list is open is a nested list.
"""

from pdf_to_markdown import (
    NumberedListAnnotator,
    NumberedListPlacement,
    NumberedListRole,
)

NONE = NumberedListPlacement()
ITEM = NumberedListPlacement(NumberedListRole.ITEM)


def continuation(indentation):
    return NumberedListPlacement(NumberedListRole.CONTINUATION, indentation)


def nested_item(indentation):
    return NumberedListPlacement(NumberedListRole.ITEM, indentation)


class TestNumberedListAnnotator:
    def test_consecutive_items_need_no_change(self):
        texts = ["1. First", "2. Second", "3. Third"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [ITEM, ITEM, ITEM]

    def test_paragraphs_between_items_are_continuations(self):
        texts = ["1. Posture", "a. Sit.", "b. Straighten.", "2. Relax", "Done."]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            continuation(3),
            continuation(3),
            ITEM,
            NONE,
        ]

    def test_item_of_a_list_that_never_started_is_marked_failed(self, caplog):
        texts = ["Some text.", "2. Set goals", "More text.", "5. Review"]
        failed = NumberedListPlacement(NumberedListRole.FAILED)
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            NONE,
            failed,
            NONE,
            failed,
        ]
        assert "belongs to no list" in caplog.text

    def test_sibling_that_is_not_a_paragraph_ends_the_list(self):
        texts = ["1. First", None, "2. Second"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            NONE,
            NumberedListPlacement(NumberedListRole.FAILED),
        ]

    def test_next_item_too_far_away_is_not_a_continuation(self):
        distance = NumberedListAnnotator.MAX_PARAGRAPHS_BETWEEN_ITEMS
        texts = ["1. First"] + ["Text."] * (distance + 1) + ["2. Second"]
        placements = NumberedListAnnotator().heuristic_annotate(texts)
        assert set(placements[1:-1]) == {NONE}

    def test_other_list_separated_by_prose_does_not_extend_the_list_above(self):
        texts = ["1. A", "2. B", "3. C", "Text.", "1. D", "2. E", "3. F", "4. G"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            ITEM,
            ITEM,
            NONE,
            ITEM,
            ITEM,
            ITEM,
            ITEM,
        ]

    def test_numbering_restarting_at_one_is_a_nested_list(self):
        texts = ["1. A", "2. B:", "1. x", "2. y", "3. z", "Detail of z.", "3. C"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            ITEM,
            nested_item(3),
            nested_item(3),
            nested_item(3),
            continuation(3),
            ITEM,
        ]

    def test_paragraph_closing_a_nested_list_belongs_to_the_outer_item(self):
        texts = ["1. A", "1. x", "2. y", "Outer detail.", "2. B"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            nested_item(3),
            nested_item(3),
            continuation(3),
            ITEM,
        ]

    def test_indent_helper(self):
        assert NumberedListAnnotator.indent("a. Sit", 3) == "   a. Sit"


TABLE = NumberedListAnnotator.TABLE_SIBLING


class TestTableInsideAList:
    def test_table_and_paragraph_between_two_items_belong_to_the_item_above(self):
        texts = ["1. One", "2. Align:", TABLE, "Comment on the table.", "3. Next"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            ITEM,
            continuation(3),
            continuation(3),
            ITEM,
        ]

    def test_table_without_following_item_ends_the_list(self):
        texts = ["1. One", TABLE, "Text after the table.", "3. Out of order"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            NONE,
            NONE,
            NumberedListPlacement(NumberedListRole.FAILED),
        ]

    def test_table_outside_of_any_list_is_left_untouched(self):
        texts = ["Some text.", TABLE, "More text."]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [NONE] * 3

    def test_table_inside_a_nested_list_is_indented_like_the_item_above(self):
        texts = ["1. Outer", "1. Inner", TABLE, "2. Next inner"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            nested_item(3),
            continuation(6),
            nested_item(3),
        ]

    def test_other_sibling_still_ends_the_list(self):
        texts = ["1. One", None, TABLE, "2. Two"]
        assert NumberedListAnnotator().heuristic_annotate(texts) == [
            ITEM,
            NONE,
            NONE,
            NumberedListPlacement(NumberedListRole.FAILED),
        ]


class TestIsNextItem:
    def test_item_following_the_last_item(self):
        texts = ["1. First", "continuation", "2. Second", "more text"]
        assert NumberedListAnnotator().heuristic_is_next_item(texts, "3. Third")

    def test_number_not_following_the_last_item(self):
        texts = ["1. First", "2. Second"]
        assert not NumberedListAnnotator().heuristic_is_next_item(texts, "5. Fifth")

    def test_text_that_is_not_an_item(self):
        assert not NumberedListAnnotator().heuristic_is_next_item(
            ["1. First"], "the end of"
        )

    def test_no_item_among_the_preceding_paragraphs(self):
        assert not NumberedListAnnotator().heuristic_is_next_item(
            ["Text."], "2. Second"
        )


class TestHeuristicsSwitch:
    def test_enabled_by_default(self):
        from pdf_to_markdown import StructuralInfoBase

        assert StructuralInfoBase.numbered_list_heuristics_enabled.fget(None) is True


class TestFailureNote:
    def test_original_number_kept_and_note_appended(self):
        assert NumberedListAnnotator.annotate_failure("4. Review") == (
            "4. Review <!-- Converter note: failing on ordered list -->"
        )

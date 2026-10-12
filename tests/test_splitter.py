"""Tests for the structural-splitting pipeline stage.

Splitter classes break raw chapter or paragraph text on regex patterns.
These tests operate on structural text (arbitrary chapter/paragraph content),
not on sentence-level text — the patterns are stage-specific.
"""

from pdf_to_markdown import (
    NameLessSinglePatternSplitter,
    MultiplePatternSplitter,
    SinglePatternSplitter,
)


class TestSinglePatternSplitter:
    def test_holds_new_sublevels_when_pattern_matches(self):
        splitter = SinglePatternSplitter(r"\n## ", r"## (.+)\n")
        assert splitter.holds_new_sublevels("intro\n## Section\ntext") is True

    def test_holds_new_sublevels_false_when_no_match(self):
        splitter = SinglePatternSplitter(r"\n## ", r"## (.+)\n")
        assert splitter.holds_new_sublevels("plain text with no heading") is False

    def test_split_at_middle_produces_two_parts(self):
        splitter = SinglePatternSplitter(r"\n## Section\n", r"## Section")
        parts = splitter.split("intro\n## Section\nbody")
        assert len(parts) == 3  # "intro", "\n## Section\n", "body"
        assert "intro" in parts
        assert "body" in parts

    def test_split_strips_empty_leading_part(self):
        # When the separator matches at the very start, re.split produces an
        # empty leading element that must be removed.
        splitter = SinglePatternSplitter(r"\n    ", r"\n    ")
        parts = splitter.split("\n    First paragraph")
        assert parts[0] != ""


class TestNameLessSinglePatternSplitter:
    def test_split_no_match_returns_original(self):
        splitter = NameLessSinglePatternSplitter(r"\n    ")
        result = splitter.split("No paragraph break here.")
        assert result == ["No paragraph break here."]

    def test_split_at_start_removes_separator(self):
        # Separator at the very start: double-removal logic (lines 76-86 of
        # Splitter.py) removes both the leading empty string and the separator.
        splitter = NameLessSinglePatternSplitter(r"\n    ")
        result = splitter.split("\n    First.\n    Second.")
        # The leading separator and empty string are both removed.
        assert result[0] != ""
        assert result[0] != "\n    "

    def test_get_sublevel_name_returns_none(self):
        splitter = NameLessSinglePatternSplitter(r"\n    ")
        assert splitter.get_sublevel_name("anything") is None

    def test_split_two_paragraphs(self):
        splitter = NameLessSinglePatternSplitter(r"\n    ")
        result = splitter.split("First paragraph.\n    Second paragraph.")
        assert len(result) == 2
        assert result[0] == "First paragraph."
        assert result[1] == "Second paragraph."


class TestMultiplePatternSplitter:
    def test_holds_new_sublevels_first_pattern(self):
        splitter = MultiplePatternSplitter([r"\n## ", r"\n### "], r"#{2,3} (.+)")
        assert splitter.holds_new_sublevels("text\n## Heading\nmore") is True

    def test_holds_new_sublevels_second_pattern(self):
        splitter = MultiplePatternSplitter([r"\n## ", r"\n### "], r"#{2,3} (.+)")
        assert splitter.holds_new_sublevels("text\n### Sub\nmore") is True

    def test_holds_new_sublevels_false_when_nothing_matches(self):
        splitter = MultiplePatternSplitter([r"\n## ", r"\n### "], r"#{2,3} (.+)")
        assert splitter.holds_new_sublevels("plain text") is False

    def test_split_on_first_pattern_only(self):
        splitter = MultiplePatternSplitter([r"\n## ", r"\n### "], r"#{2,3} (.+)")
        result = splitter.split("intro\n## Section\nbody")
        assert any("intro" in part for part in result)

    def test_split_on_both_patterns(self):
        splitter = MultiplePatternSplitter([r"\n## ", r"\n### "], r"#{2,3} (.+)")
        result = splitter.split("intro\n## H2\nbody\n### H3\nmore")
        # At least 3 parts: intro, h2 block, h3 block
        assert len(result) >= 3

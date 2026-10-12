"""Tests for the chapter-name normalization pipeline stage.

Chapter names are raw strings extracted directly from PDF pages. The rules
applied here (mid-uppercase-word newline collapse, diacritic folding, etc.)
must NOT be applied at the sentence level, where newlines have different
semantics.
"""

import pytest

from pdf_to_markdown import TextSanitizer

from .fixtures.text_examples import CHAPTER_NAME_EXAMPLES


@pytest.mark.parametrize("raw_name,expected", CHAPTER_NAME_EXAMPLES)
def test_normalize_chapter_name(raw_name, expected):
    assert TextSanitizer.normalize_chapter_name(raw_name) == expected


def test_normalize_chapter_name_mid_word_uppercase_collapse():
    # A PDF renderer sometimes breaks a single word across lines when both
    # neighbours are uppercase letters (e.g. "AWAK\nENING" → "AWAKENING").
    # This collapse is context-specific to chapter names.
    assert TextSanitizer.normalize_chapter_name("AWAK\nENING") == "AWAKENING"


def test_normalize_chapter_name_inter_word_newline_becomes_space():
    # A newline between two words in a chapter title is a visual line-break,
    # not a word-join — it must become a space.
    assert TextSanitizer.normalize_chapter_name("The\nWay") == "The Way"


def test_normalize_chapter_name_mixed_split_and_diacritic():
    # Both rules apply in sequence: mid-word collapse then diacritic fold.
    # ā (U+0101, Pali macron-a) precedes the split; W and K are ASCII uppercase.
    assert TextSanitizer.normalize_chapter_name("āWAK\nENING") == "aWAKENING"

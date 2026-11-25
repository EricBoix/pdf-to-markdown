"""LevelBreaker and the parts a splitter cuts the text of a level into."""

import dataclasses

import pytest

from pdf_to_markdown import (
    ExtractedPage,
    PageLayout,
    Part,
    PartKind,
    SinglePatternSplitter,
    SubChapterOfParagraphs,
    SuperChapter,
)
from pdf_to_markdown.LevelBreaker import LevelBreaker, TextWithLayout


def test_part_is_a_value():
    assert Part(PartKind.TABLE, "TABLE 1") == Part(PartKind.TABLE, "TABLE 1")
    assert Part(PartKind.TABLE, "TABLE 1") != Part(PartKind.HEADING, "TABLE 1")
    assert Part(PartKind.PARAGRAPH, "Text.").kind is PartKind.PARAGRAPH
    assert Part(PartKind.PARAGRAPH, "Text.").text == "Text."


def test_part_cannot_be_modified():
    part = Part(PartKind.PARAGRAPH, "Text.")
    with pytest.raises(dataclasses.FrozenInstanceError):
        part.text = "Other text."


def test_text_before_the_first_sub_chapter_is_given_to_the_paragraph_breaker():
    """A super chapter may start with text that no sub-chapter name precedes: it
    gets paragraphs of its own, from the text and the layout of its page."""
    super_chapter = SuperChapter("Part One")
    page_layout = PageLayout("iv", 3)
    page = ExtractedPage(3, page_layout, None)
    page.set_text("Introduction without a name.\n1. Alpha\nThe body of alpha.")
    super_chapter.add_page(page)

    broken_paragraph_contents = []

    def sub_chapter_factory(layout):
        sub_chapter = SubChapterOfParagraphs("")
        sub_chapter.page_layout = layout
        return sub_chapter

    LevelBreaker(
        level=super_chapter,
        level_splitter=SinglePatternSplitter(r"\d+\. [A-Za-z ]+\n", r"[A-Za-z ]+"),
        sublevel_factory=sub_chapter_factory,
        break_level_callback=lambda level: None,
        break_paragraphs_callback=lambda level, contents: (
            broken_paragraph_contents.extend(contents)
        ),
    ).break_into_sublevels()

    assert len(broken_paragraph_contents) == 1
    content = broken_paragraph_contents[0]
    assert isinstance(content, TextWithLayout)
    assert content.text == "Introduction without a name.\n"
    assert content.page_layout.page_number == 3
    assert content.page_layout.reader_page_number == "iv"
    assert [sub_chapter.name for sub_chapter in super_chapter.get_sublevels()] == [
        "Alpha"
    ]

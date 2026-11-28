"""leaves_in_reading_order: the paragraphs, tables and headings under a level."""

import pytest

from pdf_to_markdown import (
    BlockQuoteParagraph,
    ConverterError,
    ExtractedPage,
    Heading,
    PageLayout,
    Paragraph,
    ParagraphMerger,
    Sentence,
    StructuralInfoBase,
    SubChapterOfParagraphs,
    SuperChapter,
    Table,
    TopLevelChapterOfParagraphs,
)


def _layout(page_number=1):
    return PageLayout(page_number, page_number)


def _paragraph(paragraph_class=Paragraph, page_number=1):
    paragraph = paragraph_class(_layout(page_number))
    paragraph.add_sublevel(Sentence("A sentence.", _layout(page_number)))
    return paragraph


def _table():
    return Table(_layout(), "a table", None, False, [["cell"]])


def _heading():
    return Heading(_layout(), "A Title")


def test_leaves_of_a_chapter_come_in_reading_order():
    chapter = TopLevelChapterOfParagraphs("Chapter")
    first = _paragraph()
    quote = _paragraph(BlockQuoteParagraph)
    table = _table()
    heading = _heading()
    last = _paragraph()
    for leaf in (first, quote, table, heading, last):
        chapter.add_sublevel(leaf)
    assert list(chapter.leaves_in_reading_order()) == [
        first,
        quote,
        table,
        heading,
        last,
    ]


def test_leaves_are_found_whatever_their_depth():
    super_chapter = SuperChapter("Super chapter")
    direct = _paragraph()
    first_sub_chapter = SubChapterOfParagraphs("First")
    in_first = _paragraph()
    table = _table()
    first_sub_chapter.add_sublevel(in_first)
    first_sub_chapter.add_sublevel(table)
    second_sub_chapter = SubChapterOfParagraphs("Second")
    heading = _heading()
    quote = _paragraph(BlockQuoteParagraph)
    second_sub_chapter.add_sublevel(heading)
    second_sub_chapter.add_sublevel(quote)
    for sublevel in (direct, first_sub_chapter, second_sub_chapter):
        super_chapter.add_sublevel(sublevel)
    assert list(super_chapter.leaves_in_reading_order()) == [
        direct,
        in_first,
        table,
        heading,
        quote,
    ]


def test_a_paragraph_is_a_leaf_whose_sentences_are_not_visited():
    chapter = TopLevelChapterOfParagraphs("Chapter")
    chapter.add_sublevel(_paragraph())
    assert all(
        not isinstance(leaf, Sentence) for leaf in chapter.leaves_in_reading_order()
    )


def test_level_without_sublevel_has_no_leaf():
    assert list(SuperChapter("Empty").leaves_in_reading_order()) == []
    sub_chapter_without_content = SubChapterOfParagraphs("Empty")
    super_chapter = SuperChapter("Super chapter")
    super_chapter.add_sublevel(sub_chapter_without_content)
    assert list(super_chapter.leaves_in_reading_order()) == []


def test_something_else_than_a_level_or_a_leaf_is_reported():
    chapter = TopLevelChapterOfParagraphs("Chapter")
    chapter.add_sublevel(Sentence("Not expected here.", _layout()))
    with pytest.raises(ConverterError, match="Sentence found among the sublevels"):
        list(chapter.leaves_in_reading_order())


class _StructuralInfo(StructuralInfoBase):
    total_page_number = 2
    pages_info = {}


def test_chapter_without_content_is_left_alone_by_the_merger(caplog):
    # The walkers of the merger used to fail on a chapter that holds no
    # sublevel at all ('NoneType' object is not iterable).
    chapter = TopLevelChapterOfParagraphs("Chapter")
    for page_number in (1, 2):
        chapter.add_page(ExtractedPage(page_number, _layout(page_number), None))
    merger = ParagraphMerger(_StructuralInfo())
    with caplog.at_level("WARNING", logger="pdf_to_markdown"):
        merger.reconstitute_paragraphs_spreading_over_two_pages(chapter)
        merger.reconstitute_blockquotes_spreading_over_two_pages(chapter)
    assert chapter.get_sublevels() is None
    assert "No paragraph with page number 2 found" in caplog.text

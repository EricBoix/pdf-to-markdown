"""A blockquote (pull quote) cut by a page break is reconstituted by ParagraphMerger."""

from pdf_to_markdown import (
    BlockQuoteParagraph,
    ExtractedPage,
    PageLayout,
    Paragraph,
    ParagraphMerger,
    Sentence,
    TopLevelChapterOfParagraphs,
)


def _paragraph(paragraph_class, page_number, *sentence_texts):
    paragraph = paragraph_class(PageLayout(page_number + 1, page_number))
    for sentence_text in sentence_texts:
        paragraph.add_sublevel(
            Sentence(sentence_text, PageLayout(page_number + 1, page_number))
        )
    paragraph.renumber_sublevels()
    return paragraph


class _StructuralInfo:
    def __init__(self, pages_info=None, new_chapter_pages=()):
        self.pages_info = pages_info if pages_info is not None else {}
        self._new_chapter_pages = new_chapter_pages

    def _get_page_number_finishing_last_paragraph(self, page_number):
        next_page_number = page_number + 1
        while (
            next_page_number in self.pages_info
            and "drop_page" in self.pages_info[next_page_number]
        ):
            next_page_number += 1
        return next_page_number

    def _holds_new_chapter(self, page_number):
        return page_number in self._new_chapter_pages


def _merge(structural_info, page_numbers, *paragraphs):
    chapter = TopLevelChapterOfParagraphs("Chapter")
    for page_number in page_numbers:
        chapter.add_page(
            ExtractedPage(page_number, PageLayout(page_number + 1, page_number), None)
        )
    for paragraph in paragraphs:
        chapter.add_sublevel(paragraph)
    chapter.renumber_sublevels()
    ParagraphMerger(structural_info).reconstitute_blockquotes_spreading_over_two_pages(
        chapter
    )
    return chapter.get_sublevels()


def test_blockquote_cut_by_a_page_break_is_merged():
    first_half = _paragraph(BlockQuoteParagraph, 1, "Many minds work.", "The conscious")
    second_half = _paragraph(BlockQuoteParagraph, 2, "mind lets them cooperate.")
    remaining = _merge(_StructuralInfo(), (1, 2), first_half, second_half)
    assert remaining == [first_half]
    assert [sentence.text for sentence in first_half.get_sentences()] == [
        "Many minds work.",
        "The conscious mind lets them cooperate.",
    ]


def test_complete_blockquote_is_not_merged_with_the_next_one():
    first = _paragraph(BlockQuoteParagraph, 1, "The mind is calm.")
    second = _paragraph(BlockQuoteParagraph, 2, "Another quote follows.")
    assert _merge(_StructuralInfo(), (1, 2), first, second) == [first, second]


def test_blockquote_is_not_glued_to_a_paragraph_starting_the_next_page():
    quote = _paragraph(BlockQuoteParagraph, 1, "An unfinished")
    paragraph = _paragraph(Paragraph, 2, "running text.")
    assert _merge(_StructuralInfo(), (1, 2), quote, paragraph) == [quote, paragraph]


def test_veto_flag_prevents_the_merge():
    first_half = _paragraph(BlockQuoteParagraph, 1, "An unfinished")
    second_half = _paragraph(BlockQuoteParagraph, 2, "quote.")
    structural_info = _StructuralInfo({1: {"blockquote_fits_on_page": True}})
    assert _merge(structural_info, (1, 2), first_half, second_half) == [
        first_half,
        second_half,
    ]


def test_blockquote_is_not_merged_across_a_chapter_start():
    first_half = _paragraph(BlockQuoteParagraph, 1, "An unfinished")
    second_half = _paragraph(BlockQuoteParagraph, 2, "quote.")
    structural_info = _StructuralInfo(new_chapter_pages=(2,))
    assert _merge(structural_info, (1, 2), first_half, second_half) == [
        first_half,
        second_half,
    ]


def test_blockquote_is_merged_across_a_skipped_page():
    first_half = _paragraph(BlockQuoteParagraph, 1, "An unfinished")
    second_half = _paragraph(BlockQuoteParagraph, 3, "quote.")
    structural_info = _StructuralInfo({2: {"drop_page": True}})
    assert _merge(structural_info, (1, 2, 3), first_half, second_half) == [first_half]
    assert first_half.get_sentences()[-1].text == "An unfinished quote."

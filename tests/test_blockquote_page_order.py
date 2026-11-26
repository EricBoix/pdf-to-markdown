"""A pull quote standing between the two halves of a paragraph cut by a page break
must not end up after text of the next page (the pages of the markdown must not
go backwards)."""

from pdf_to_markdown import (
    BlockQuoteParagraph,
    ExtractedPage,
    PageLayout,
    Paragraph,
    ParagraphMerger,
    Sentence,
    StructuralInfoBase,
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


class _StructuralInfo(StructuralInfoBase):
    total_page_number = 3

    @property
    def pages_info(self) -> dict:
        return {}

    def _holds_new_chapter(self, page_number):
        return False


def _merge_paragraphs(*leaves):
    chapter = TopLevelChapterOfParagraphs("Chapter")
    for page_number in (1, 2):
        chapter.add_page(
            ExtractedPage(page_number, PageLayout(page_number + 1, page_number), None)
        )
    for leaf in leaves:
        chapter.add_sublevel(leaf)
    chapter.renumber_sublevels()
    ParagraphMerger(_StructuralInfo()).reconstitute_paragraphs_spreading_over_two_pages(
        chapter
    )
    return chapter.get_sublevels()


def _page_numbers_of_sentences(leaves):
    return [
        sentence.page_layout.page_number
        for leaf in leaves
        for sentence in leaf.get_sentences()
    ]


def test_quote_of_the_first_page_moves_before_the_merged_paragraph():
    head = _paragraph(Paragraph, 1, "Something went on and", "an unfinished")
    quote = _paragraph(BlockQuoteParagraph, 1, "A pull quote.")
    tail = _paragraph(Paragraph, 2, "sentence ends here.")
    remaining = _merge_paragraphs(head, quote, tail)
    assert remaining == [quote, head]
    page_numbers = _page_numbers_of_sentences(remaining)
    assert page_numbers == sorted(page_numbers)
    assert [leaf.number for leaf in remaining] == [1, 2]


def test_quote_of_the_next_page_stays_in_place():
    head = _paragraph(Paragraph, 1, "An unfinished")
    quote = _paragraph(BlockQuoteParagraph, 2, "A pull quote.")
    tail = _paragraph(Paragraph, 2, "sentence ends here.")
    assert _merge_paragraphs(head, quote, tail) == [head, quote]


def test_nothing_moves_without_a_quote_between_the_halves():
    head = _paragraph(Paragraph, 1, "An unfinished")
    tail = _paragraph(Paragraph, 2, "sentence ends here.")
    assert _merge_paragraphs(head, tail) == [head]

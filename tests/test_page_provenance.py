"""Every Sentence keeps the page it comes from, on the tree.

Two page notions are carried by a PageLayout: the pdf (paper) page index, always
an int, and the page number printed on the page, an int or a str (e.g. "Cover"
or roman numerals for the front matter of a book). The consumer decides which
one it refers to, so both must survive on each sentence, also when a paragraph
cut by a page break is reconstituted.
"""

from pdf_to_markdown import (
    ExtractedPage,
    PageLayout,
    Paragraph,
    ParagraphMerger,
    Sentence,
    StructuralInfoBase,
    TopLevelChapterOfParagraphs,
)

from .fixtures.fixture_structural_info import DeclaresTheMergeRules


def _paragraph(reader_page_number, page_number, *sentence_texts):
    paragraph = Paragraph(PageLayout(reader_page_number, page_number))
    for sentence_text in sentence_texts:
        paragraph.add_sublevel(
            Sentence(sentence_text, PageLayout(reader_page_number, page_number))
        )
    paragraph.renumber_sublevels()
    return paragraph


class _StructuralInfo(DeclaresTheMergeRules, StructuralInfoBase):
    total_page_number = 3

    def __init__(self, pages_info=None):
        super().__init__()
        self._declared_pages_info = pages_info if pages_info is not None else {}

    @property
    def pages_info(self) -> dict:
        return self._declared_pages_info


def _merge_paragraphs(structural_info, pages, *paragraphs):
    """The paragraphs merged across the page breaks of the given pages, each
    page being a (reader_page_number, page_number) pair."""
    chapter = TopLevelChapterOfParagraphs("Chapter")
    for reader_page_number, page_number in pages:
        chapter.add_page(
            ExtractedPage(
                page_number, PageLayout(reader_page_number, page_number), None
            )
        )
    for paragraph in paragraphs:
        chapter.add_sublevel(paragraph)
    chapter.renumber_sublevels()
    ParagraphMerger(structural_info).reconstitute_paragraphs_spreading_over_two_pages(
        chapter
    )
    return chapter.get_sublevels()


def _sentence_pages(paragraph):
    return [
        (sentence.page_layout.reader_page_number, sentence.page_layout.page_number)
        for sentence in paragraph.get_sentences()
    ]


def test_sentence_keeps_a_non_numeric_printed_page_number_next_to_the_pdf_index():
    cover = Sentence("A cover sentence.", PageLayout("Cover", 0))
    front_matter = Sentence("A preface sentence.", PageLayout("iv", 4))
    body = Sentence("A body sentence.", PageLayout(12, 20))
    assert (cover.page_layout.reader_page_number, cover.page_layout.page_number) == (
        "Cover",
        0,
    )
    assert (
        front_matter.page_layout.reader_page_number,
        front_matter.page_layout.page_number,
    ) == ("iv", 4)
    assert (body.page_layout.reader_page_number, body.page_layout.page_number) == (
        12,
        20,
    )


def test_merged_paragraph_keeps_the_page_of_each_sentence():
    first_half = _paragraph("iv", 3, "Many minds work.", "The conscious")
    second_half = _paragraph("v", 4, "mind lets them cooperate.", "It is calm.")
    remaining = _merge_paragraphs(
        _StructuralInfo(), (("iv", 3), ("v", 4)), first_half, second_half
    )
    assert remaining == [first_half]
    assert [sentence.text for sentence in first_half.get_sentences()] == [
        "Many minds work.",
        "The conscious mind lets them cooperate.",
        "It is calm.",
    ]
    # The sentence cut by the page break is attributed to the page where it
    # starts, the sentence that follows keeps the page it is printed on.
    assert _sentence_pages(first_half) == [("iv", 3), ("iv", 3), ("v", 4)]


def test_paragraph_merged_across_a_skipped_page_keeps_the_pdf_index_of_each_sentence():
    first_half = _paragraph("iv", 3, "An unfinished")
    second_half = _paragraph("vi", 5, "sentence.", "A complete one.")
    structural_info = _StructuralInfo({4: {"drop_page": True}})
    remaining = _merge_paragraphs(
        structural_info, (("iv", 3), ("v", 4), ("vi", 5)), first_half, second_half
    )
    assert remaining == [first_half]
    assert _sentence_pages(first_half) == [("iv", 3), ("vi", 5)]

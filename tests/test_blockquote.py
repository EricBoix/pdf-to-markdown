"""Tests for the blockquote (e.g. pull quote) handling of pdf documents.

A blockquote is detected at the splitting stage (ParagraphAndBlockquoteSplitter),
it must not disturb the reconstitution of the paragraphs that spread over two
pages (ParagraphMerger) and it is dropped when it merely repeats a paragraph
(BlockquoteDeduplicator).
"""

from pdf_to_markdown import (
    BlockQuoteParagraph,
    BlockquoteDeduplicator,
    Document,
    ExtractedPage,
    PageLayout,
    Paragraph,
    ParagraphAndBlockquoteSplitter,
    PartKind,
    ParagraphMerger,
    Sentence,
    TopLevelChapterOfParagraphs,
    StructuralInfoBase,
)

PARAGRAPH_BREAKING_PATTERN = "\n   "
BLOCKQUOTE_PATTERN = r"(?:\A|\n\n)((?: {4}\S(?:(?! {5})[^\n])*(?:\n|\Z))+)(?=\n|\Z)"


class TestParagraphAndBlockquoteSplitter:
    def _splitter(self):
        return ParagraphAndBlockquoteSplitter(
            PARAGRAPH_BREAKING_PATTERN, BLOCKQUOTE_PATTERN
        )

    def test_blockquote_lines_are_kept_together_and_flagged(self):
        splitter = self._splitter()
        text = (
            "First paragraph\nover two lines.\n"
            "\n"
            "    The pull quote starts\n"
            "    and ends here.\n"
            "\n"
            "   Second paragraph.\n"
        )
        parts = splitter.split(text)
        assert [part.kind is PartKind.BLOCKQUOTE for part in parts] == [
            False,
            True,
            False,
        ]
        assert "The pull quote starts" in parts[1].text
        assert "and ends here." in parts[1].text
        assert parts[0].text.startswith("First paragraph")
        assert parts[2].text.startswith("Second paragraph")

    def test_text_without_blockquote_is_split_like_paragraphs(self):
        splitter = self._splitter()
        parts = splitter.split("   One.\n   Two.\n")
        assert len(parts) == 2
        assert not any(part.kind is PartKind.BLOCKQUOTE for part in parts)

    def test_paragraph_beginning_is_not_a_blockquote(self):
        # Paragraphs begin with exactly three spaces (not four), and are not
        # preceded by a blank line.
        splitter = self._splitter()
        parts = splitter.split("Continuation.\n   New paragraph.\n   Another.\n")
        assert not any(part.kind is PartKind.BLOCKQUOTE for part in parts)

    def test_blockquote_at_the_top_of_a_page(self):
        splitter = self._splitter()
        parts = splitter.split(
            "    Quote at the top\n    of the page.\n\n   Then a paragraph.\n"
        )
        assert [part.kind is PartKind.BLOCKQUOTE for part in parts] == [True, False]

    def test_blockquote_at_the_bottom_of_a_page(self):
        splitter = self._splitter()
        parts = splitter.split("   A paragraph.\n\n    Quote at the bottom.\n")
        assert [part.kind is PartKind.BLOCKQUOTE for part in parts] == [False, True]

    def test_table_like_lines_are_not_a_blockquote(self):
        splitter = self._splitter()
        parts = splitter.split(
            "   Intro.\n\n    Left column          Right column\n\n   Outro.\n"
        )
        assert not any(part.kind is PartKind.BLOCKQUOTE for part in parts)


class TestTextExtractionLeadingWhitespace:
    class _StructuralInfo(StructuralInfoBase):
        pages_info = {}
        total_page_number = 1

    def test_default_removes_all_leading_whitespace(self):
        assert (
            self._StructuralInfo().strip_page_text_leading_whitespace("\n\n    text")
            == "text"
        )


def _sentence(text, page_number):
    return Sentence(text, PageLayout(page_number + 1, page_number))


def _paragraph(paragraph_class, page_number, *sentence_texts):
    paragraph = paragraph_class(PageLayout(page_number + 1, page_number))
    for sentence_text in sentence_texts:
        paragraph.add_sublevel(_sentence(sentence_text, page_number))
    paragraph.renumber_sublevels()
    return paragraph


def _document_of(*paragraphs):
    document = Document("Test")
    chapter = TopLevelChapterOfParagraphs("Chapter")
    document.add_chapter(chapter)
    for paragraph in paragraphs:
        chapter.add_sublevel(paragraph)
    chapter.renumber_sublevels()
    return document, chapter


class TestBlockquoteDeduplicator:
    def _deduplicate(self, *paragraphs):
        document, chapter = _document_of(*paragraphs)
        BlockquoteDeduplicator().remove_duplicated_blockquotes(document)
        return chapter.get_sublevels()

    def test_blockquote_repeating_the_beginning_of_a_paragraph_is_dropped(self):
        paragraph = _paragraph(
            Paragraph, 1, "It is stable.", "It is clear.", "Indeed, it is deep."
        )
        blockquote = _paragraph(BlockQuoteParagraph, 1, "It is stable. It is clear.")
        assert self._deduplicate(blockquote, paragraph) == [paragraph]

    def test_blockquote_repeating_sentences_in_the_middle_is_dropped(self):
        paragraph = _paragraph(Paragraph, 1, "First one.", "Second one.", "Third one.")
        blockquote = _paragraph(BlockQuoteParagraph, 1, "Second one.")
        assert self._deduplicate(paragraph, blockquote) == [paragraph]

    def test_blockquote_repeating_a_whole_paragraph_is_dropped(self):
        paragraph = _paragraph(Paragraph, 1, "Only sentence.")
        blockquote = _paragraph(BlockQuoteParagraph, 1, "Only sentence.")
        assert self._deduplicate(paragraph, blockquote) == [paragraph]

    def test_normalization_ignores_whitespace_and_typographic_quotes(self):
        paragraph = _paragraph(Paragraph, 1, "It’s non- perceiving.")
        blockquote = _paragraph(BlockQuoteParagraph, 1, "It's non-perceiving.")
        assert self._deduplicate(paragraph, blockquote) == [paragraph]

    def test_blockquote_matching_a_fragment_of_a_sentence_is_kept(self):
        paragraph = _paragraph(Paragraph, 1, "Success leads to trust in practice.")
        blockquote = _paragraph(BlockQuoteParagraph, 1, "Success leads to trust.")
        assert self._deduplicate(paragraph, blockquote) == [paragraph, blockquote]

    def test_paraphrased_blockquote_is_kept(self):
        paragraph = _paragraph(Paragraph, 1, "The objects of consciousness arise.")
        blockquote = _paragraph(
            BlockQuoteParagraph, 1, "Objects of consciousness arise."
        )
        assert self._deduplicate(paragraph, blockquote) == [paragraph, blockquote]

    def test_paragraph_of_previous_and_next_pages_are_in_scope(self):
        previous_page = _paragraph(Paragraph, 1, "Before.")
        next_page = _paragraph(Paragraph, 3, "After.")
        blockquote_of_previous = _paragraph(BlockQuoteParagraph, 2, "Before.")
        blockquote_of_next = _paragraph(BlockQuoteParagraph, 2, "After.")
        assert self._deduplicate(
            previous_page, blockquote_of_previous, blockquote_of_next, next_page
        ) == [previous_page, next_page]

    def test_paragraph_two_pages_away_is_out_of_scope(self):
        far_paragraph = _paragraph(Paragraph, 1, "Far away.")
        blockquote = _paragraph(BlockQuoteParagraph, 3, "Far away.")
        assert self._deduplicate(far_paragraph, blockquote) == [
            far_paragraph,
            blockquote,
        ]

    def test_blockquotes_are_not_compared_to_each_other(self):
        first = _paragraph(BlockQuoteParagraph, 1, "Same text.")
        second = _paragraph(BlockQuoteParagraph, 1, "Same text.")
        assert self._deduplicate(first, second) == [first, second]

    def test_sublevels_are_renumbered_after_a_drop(self):
        paragraph = _paragraph(Paragraph, 1, "Kept.")
        blockquote = _paragraph(BlockQuoteParagraph, 1, "Kept.")
        other = _paragraph(Paragraph, 1, "Other.")
        remaining = self._deduplicate(paragraph, blockquote, other)
        assert [sublevel.number for sublevel in remaining] == [1, 2]


class TestParagraphMergerIgnoresBlockquotes:
    class _StructuralInfo(StructuralInfoBase):
        pages_info = {}
        total_page_number = 2
        numbered_list_heuristics_enabled = True

        def _get_page_number_finishing_last_paragraph(self, page_number):
            return page_number + 1

        def _holds_new_chapter(self, page_number):
            return False

    def _merge(self, *paragraphs):
        chapter = TopLevelChapterOfParagraphs("Chapter")
        for page_number in (1, 2):
            chapter.add_page(
                ExtractedPage(
                    page_number, PageLayout(page_number + 1, page_number), None
                )
            )
        for paragraph in paragraphs:
            chapter.add_sublevel(paragraph)
        chapter.renumber_sublevels()
        ParagraphMerger(
            self._StructuralInfo()
        ).reconstitute_paragraphs_spreading_over_two_pages(chapter)
        return chapter.get_sublevels()

    def test_blockquote_ending_a_page_does_not_prevent_the_merge(self):
        beginning = _paragraph(Paragraph, 1, "It is calm.", "The mind is very")
        blockquote = _paragraph(BlockQuoteParagraph, 1, "A complete quote.")
        ending = _paragraph(Paragraph, 2, "clear and deep.")
        merged = self._merge(beginning, blockquote, ending)
        assert merged == [beginning, blockquote]
        assert [sentence.text for sentence in beginning.get_sentences()] == [
            "It is calm.",
            "The mind is very clear and deep.",
        ]

    def test_blockquote_starting_a_page_is_not_merged_as_a_continuation(self):
        beginning = _paragraph(Paragraph, 1, "It is calm.", "The mind is very")
        blockquote = _paragraph(BlockQuoteParagraph, 2, "A complete quote.")
        ending = _paragraph(Paragraph, 2, "clear and deep.")
        merged = self._merge(beginning, blockquote, ending)
        assert merged == [beginning, blockquote]
        assert beginning.get_sentences()[-1].text == "The mind is very clear and deep."
        assert [sentence.text for sentence in blockquote.get_sentences()] == [
            "A complete quote."
        ]

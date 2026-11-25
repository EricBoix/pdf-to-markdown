"""Tests for the headings: titles of sub-sections that have no level of their own.

A heading is cut out of the text by the splitter (like a blockquote), it is a
flat leaf of the level holding it (like a table) written as a markdown header
one level below that level, and a page can be declared not to open a chapter
(a centered sub-title followed by blank lines looks like a chapter title).
"""

from mdutils.mdutils import MdUtils

from pdf_to_markdown import (
    ChapterSplitter,
    Document,
    ExtractedPage,
    Heading,
    HeadingText,
    NumberedListAnnotator,
    PageLayout,
    Paragraph,
    ParagraphAndBlockquoteSplitter,
    ParagraphMerger,
    Sentence,
    SectionDropper,
    StructuralInfoBase,
    SubChapterOfParagraphs,
    SuperChapter,
    TopLevelChapterOfParagraphs,
)

PARAGRAPH_BREAKING_PATTERN = "\n   "
BLOCKQUOTE_PATTERN = r"(?:\A|\n\n)((?: {4}\S(?:(?! {5})[^\n])*(?:\n|\Z))+)(?=\n|\Z)"
HEADING_PATTERN = r"(?:\A|\n) {30,}((?:(?! {3})[^\n])*[a-z](?:(?! {3})[^\n])*?) *\n{3,}"
CENTERING = " " * 45


class TestHeadingSplitting:
    def _split(self, text, heading_pattern=HEADING_PATTERN):
        return ParagraphAndBlockquoteSplitter(
            PARAGRAPH_BREAKING_PATTERN, BLOCKQUOTE_PATTERN, heading_pattern
        ).split(text)

    def test_heading_is_cut_out_between_two_paragraphs(self):
        text = (
            "\n   First paragraph.\n"
            + CENTERING
            + "A Centered Title\n\n\n\n\n"
            + "   Second paragraph.\n"
        )
        parts = self._split(text)
        assert parts == ["First paragraph.", "A Centered Title", "Second paragraph.\n"]
        splitter = ParagraphAndBlockquoteSplitter(
            PARAGRAPH_BREAKING_PATTERN, BLOCKQUOTE_PATTERN, HEADING_PATTERN
        )
        assert [splitter.is_heading(part) for part in parts] == [False, True, False]
        assert isinstance(parts[1], HeadingText)

    def test_heading_at_the_very_beginning_of_the_text(self):
        text = CENTERING + "A Centered Title\n\n\n\n\n" + "   A paragraph.\n"
        assert self._split(text) == ["A Centered Title", "A paragraph.\n"]

    def test_blockquote_following_a_heading_is_still_a_blockquote(self):
        text = (
            "\n   A paragraph.\n"
            + " " * 31
            + "A Title\n\n\n\n\n\n"
            + "    A pull quote line.\n"
            + "    Another line.\n"
            + "\n   Next paragraph.\n"
        )
        splitter = ParagraphAndBlockquoteSplitter(
            PARAGRAPH_BREAKING_PATTERN, BLOCKQUOTE_PATTERN, HEADING_PATTERN
        )
        parts = splitter.split(text)
        assert parts[:2] == ["A paragraph.", "A Title"]
        assert splitter.is_blockquote(parts[2])
        assert parts[2] == "    A pull quote line.\n    Another line.\n"
        assert parts[3].strip() == "Next paragraph."

    def test_line_followed_by_fewer_blank_lines_is_not_a_heading(self):
        text = "   First.\n" + CENTERING + "Not A Title\n\n   Second.\n"
        parts = self._split(text)
        assert not any(isinstance(part, HeadingText) for part in parts)

    def test_all_capital_line_is_not_a_heading(self):
        text = "   First.\n" + CENTERING + "ALL CAPITALS\n\n\n\n\n   Second.\n"
        parts = self._split(text)
        assert not any(isinstance(part, HeadingText) for part in parts)

    def test_without_heading_pattern_nothing_changes(self):
        text = "   First.\n" + CENTERING + "A Centered Title\n\n\n\n\n   Second.\n"
        parts = self._split(text, heading_pattern=None)
        assert not any(isinstance(part, HeadingText) for part in parts)


class TestHeadingMarkdown:
    def _markdown_of(self, document):
        md_file = MdUtils(file_name="unused")
        for chapter in document.get_chapters():
            chapter.to_markdown(md_file, level=2)
        return md_file.file_data_text

    @staticmethod
    def _paragraph(text):
        paragraph = Paragraph(PageLayout(1, 1))
        paragraph.add_sublevel(Sentence(text, PageLayout(1, 1)))
        paragraph.renumber_sublevels()
        return paragraph

    def test_heading_is_a_header_one_level_below_its_owner(self):
        subchapter = SubChapterOfParagraphs("INTRODUCTION")
        subchapter.add_sublevel(self._paragraph("Before."))
        subchapter.add_sublevel(Heading(PageLayout(1, 1), "A Title"))
        subchapter.add_sublevel(self._paragraph("After."))
        chapter = SuperChapter("Notes")
        chapter.add_chapter(subchapter)
        document = Document("Test")
        document.add_chapter(chapter)
        assert self._markdown_of(document).strip("\n").split("\n") == [
            "## Notes",
            "",
            "### INTRODUCTION",
            "",
            "Before.",
            "",
            "#### A Title",
            "",
            "After.",
        ]

    def test_heading_first_of_a_level_gets_a_single_blank_line(self):
        subchapter = SubChapterOfParagraphs("INTRODUCTION")
        subchapter.add_sublevel(Heading(PageLayout(1, 1), "A Title"))
        subchapter.add_sublevel(self._paragraph("After."))
        chapter = SuperChapter("Notes")
        chapter.add_chapter(subchapter)
        document = Document("Test")
        document.add_chapter(chapter)
        assert "\n\n\n" not in self._markdown_of(document)


class TestHeadingIsALeaf:
    def test_heading_has_no_sentences(self):
        assert Heading(PageLayout(1, 1), "A Title").get_sentences() is None

    def test_section_dropper_ignores_headings(self):
        class _StructuralInfo:
            dropped_sections = []

            def is_section_dropped(self, name):
                return False

        subchapter = SubChapterOfParagraphs("Sub")
        subchapter.add_sublevel(Heading(PageLayout(1, 1), "A Title"))
        chapter = TopLevelChapterOfParagraphs("Chapter")
        chapter.add_sublevel(subchapter)
        document = Document("Test")
        document.add_chapter(chapter)
        SectionDropper(_StructuralInfo()).drop_sections(document)
        assert subchapter.get_sublevels()[0].name == "A Title"

    def test_heading_ends_a_numbered_list(self):
        chapter = TopLevelChapterOfParagraphs("Chapter")
        texts = ["1. One", None, "2. Two"]
        assert (
            NumberedListAnnotator().heuristic_annotate(texts)[2].role.value == "failed"
        )
        # A heading is reported to the annotator as any other sibling that is
        # not a paragraph (None), see DocumentHierarchicalLevel.
        chapter.add_sublevel(Heading(PageLayout(1, 1), "A Title"))
        assert chapter._get_text_for_list_heuristics(chapter.get_sublevels()[0]) is None


class _MergerStructuralInfo(StructuralInfoBase):
    pages_info = {}
    total_page_number = 2
    numbered_list_heuristics_enabled = False

    def _get_page_number_finishing_last_paragraph(self, page_number):
        return page_number + 1

    def _holds_new_chapter(self, page_number):
        return False


class TestHeadingInterruptsTheTextFlow:
    def _chapter_with(self, *leaves):
        chapter = TopLevelChapterOfParagraphs("Chapter")
        for page_number in (1, 2):
            chapter.add_page(
                ExtractedPage(page_number, PageLayout(page_number, page_number), None)
            )
        for leaf in leaves:
            chapter.add_sublevel(leaf)
        chapter.renumber_sublevels()
        return chapter

    @staticmethod
    def _paragraph(page_number, text):
        paragraph = Paragraph(PageLayout(page_number, page_number))
        paragraph.add_sublevel(Sentence(text, PageLayout(page_number, page_number)))
        paragraph.renumber_sublevels()
        return paragraph

    def test_paragraph_is_not_glued_to_the_one_following_a_heading(self):
        ending = self._paragraph(1, "A paragraph cut by")
        heading = Heading(PageLayout(1, 1), "A Title")
        starting = self._paragraph(2, "the page break.")
        chapter = self._chapter_with(ending, heading, starting)
        ParagraphMerger(
            _MergerStructuralInfo()
        ).reconstitute_paragraphs_spreading_over_two_pages(chapter)
        assert chapter.get_sublevels() == [ending, heading, starting]


class TestNoNewChapterPage:
    # A centered title followed by blank lines is what opens the chapters
    CHAPTER_LOOKING_TEXT = "A Centered Title\n\n\n\n\n\nSome text of the page."

    class _StructuralInfo(StructuralInfoBase):
        pages_info = {
            1: {"type": "generic", "no_new_chapter": True},
            2: {
                "type": "chapter",
                "chapter_info": {"name": "Declared chapter"},
                "no_new_chapter": True,
            },
            3: {"type": "generic"},
        }
        total_page_number = 4

    def _splitter(self):
        info = self._StructuralInfo()
        return ChapterSplitter(
            info,
            r"\A\s*+(?![a-z])(?=[\s\S]{0,100}?(?:\n){3,}(?:\w| ))",
            r"((?:\n){3,}(\w| ))",
            100,
        )

    def _holds_new_chapter(self, page_number):
        page = ExtractedPage(page_number, PageLayout(page_number, page_number), None)
        page.set_text(self.CHAPTER_LOOKING_TEXT)
        return self._splitter().holds_new_chapter(page)

    def test_page_without_the_flag_opens_a_chapter(self):
        assert self._holds_new_chapter(3)
        assert self._holds_new_chapter(0)

    def test_flagged_page_does_not_open_a_chapter(self):
        assert not self._holds_new_chapter(1)

    def test_page_declared_as_a_chapter_still_opens_one(self):
        assert self._holds_new_chapter(2)

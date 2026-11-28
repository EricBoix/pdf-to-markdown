"""PageMarker and PageBreak: where the sentences come from, written in the markdown."""

import re

import pytest
from mdutils.mdutils import MdUtils

from pdf_to_markdown import (
    BlockQuoteParagraph,
    ConverterError,
    Document,
    Heading,
    PageBreak,
    PageBreakInserter,
    PageLayout,
    PageMarker,
    Paragraph,
    Sentence,
    Table,
    TopLevelChapterOfParagraphs,
)
from pdf_to_markdown.Model import DocumentHierarchicalLevel
from pdf_to_markdown.NumberedListAnnotator import (
    NumberedListAnnotator,
    NumberedListPlacement,
    NumberedListRole,
)

# The pages of the tests: a printed number (roman for the preamble) and the
# index of the page in the pdf.
PAGE_IV = PageLayout("iv", 3)
PAGE_V = PageLayout("v", 4)
PAGE_SIX = PageLayout(6, 5)

MARKER_LINE = re.compile(r"(?:\s*> |\s*)<!-- page reader=\S+ pdf=\d+ -->")


def _paragraph(*sentences, paragraph_class=Paragraph):
    """A paragraph made of (text, layout) sentences, on the page of the first."""
    paragraph = paragraph_class(sentences[0][1])
    for text, layout in sentences:
        paragraph.add_sublevel(Sentence(text, layout))
    paragraph.renumber_sublevels()
    return paragraph


def _chapter(*leaves, layout=PAGE_IV):
    chapter = TopLevelChapterOfParagraphs("Chapter")
    chapter.page_layout = layout
    for leaf in leaves:
        chapter.add_sublevel(leaf)
    chapter.renumber_sublevels()
    return chapter


def _document(chapter, maximum_line_length=None):
    """The document holding the chapter, with its page breaks."""
    document = Document("Test")
    document.add_chapter(chapter)
    document.maximum_line_length = maximum_line_length
    PageBreakInserter().insert_page_breaks(document)
    return document


def _lines(chapter, page_markers=True, maximum_line_length=None):
    """The markdown of a chapter, as lines (the blank lines kept)."""
    document = _document(chapter, maximum_line_length)
    md_file = MdUtils(file_name="unused")
    DocumentHierarchicalLevel.write_sublevels_to_markdown(
        md_file, document.get_chapters_with_page_breaks(), 2, page_markers
    )
    return md_file.file_data_text.strip("\n").split("\n")


def _kinds(level):
    """The kinds of the sublevels of a level, the page breaks included."""
    return [type(sublevel).__name__ for sublevel in level.sublevels]


class TestPageMarkerSyntax:
    def test_comment_of_an_integer_reader_page(self):
        assert PageMarker(12, 13).to_comment() == "<!-- page reader=12 pdf=13 -->"

    def test_pdf_page_is_counted_from_one_as_a_pdf_viewer_does(self):
        marker = PageMarker.from_layout(PageLayout("Cover", 0))
        assert marker == PageMarker("Cover", 1)
        assert marker.to_comment() == "<!-- page reader=Cover pdf=1 -->"

    @pytest.mark.parametrize("reader", [12, "iv", "Cover", "A b", "a-->b", "50%"])
    def test_comment_is_parsed_back(self, reader):
        marker = PageMarker(reader, 7)
        assert PageMarker.parse(marker.to_comment()) == marker

    def test_reader_page_that_is_not_plain_text_is_percent_encoded(self):
        comment = PageMarker("a b-->", 7).to_comment()
        assert comment == "<!-- page reader=a%20b--%3E pdf=7 -->"
        assert comment.count("-->") == 1

    def test_digits_are_read_back_as_an_integer(self):
        assert (
            PageMarker.parse("<!-- page reader=12 pdf=13 -->").reader_page_number == 12
        )

    def test_other_comments_are_not_page_markers(self):
        assert PageMarker.parse("<!-- Converter note: picture removed -->") is None
        assert PageMarker.parse("<!-- omit from pdf-to-markdown: practical -->") is None


class TestPageBreak:
    def test_comment_is_the_marker_of_the_page(self):
        assert PageBreak(PAGE_IV).comment == "<!-- page reader=iv pdf=4 -->"

    def test_a_page_break_has_no_sentences(self):
        assert PageBreak(PAGE_IV).get_sentences() is None

    def test_a_page_break_holds_a_copy_of_the_layout(self):
        layout = PageLayout("iv", 3)
        page_break = PageBreak(layout)
        assert page_break.page_layout.page_number == layout.page_number
        assert page_break.page_layout.reader_page_number == layout.reader_page_number
        assert page_break.page_layout is not layout


class TestPageBreakInserter:
    def test_first_text_gets_a_page_break_then_only_changes_of_page(self):
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV)),
            _paragraph(("Second.", PAGE_V)),
            _paragraph(("Third.", PAGE_V)),
        )
        document = _document(chapter)
        assert _kinds(document) == ["PageBreak", "TopLevelChapterOfParagraphs"]
        assert _kinds(chapter) == ["Paragraph", "PageBreak", "Paragraph", "Paragraph"]
        assert [
            page_break.page_layout.page_number
            for page_break in (document.sublevels[0], chapter.sublevels[1])
        ] == [3, 4]

    def test_page_break_within_a_paragraph_stands_before_the_sentence(self):
        paragraph = _paragraph(
            ("First.", PAGE_IV), ("Second.", PAGE_IV), ("Third.", PAGE_V)
        )
        _document(_chapter(paragraph))
        assert _kinds(paragraph) == ["Sentence", "Sentence", "PageBreak", "Sentence"]

    def test_page_breaks_are_no_element_of_the_document(self):
        paragraph = _paragraph(("First.", PAGE_IV), ("Second.", PAGE_V))
        chapter = _chapter(paragraph, _paragraph(("Third.", PAGE_V)))
        document = _document(chapter)
        assert document.get_chapters() == [chapter]
        assert len(chapter.get_sublevels()) == 2
        assert [sentence.text for sentence in paragraph.get_sentences()] == [
            "First.",
            "Second.",
        ]
        assert [sentence.number for sentence in paragraph.get_sentences()] == [1, 2]

    def test_page_breaks_do_not_shift_the_numbers(self):
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV)), _paragraph(("Second.", PAGE_V))
        )
        _document(chapter)
        chapter.renumber_sublevels()
        assert [leaf.number for leaf in chapter.get_sublevels()] == [1, 2]

    def test_leaves_in_reading_order_yield_the_page_breaks_between_leaves(self):
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV)), _paragraph(("Second.", PAGE_V))
        )
        _document(chapter)
        assert [type(leaf).__name__ for leaf in chapter.leaves_in_reading_order()] == [
            "Paragraph",
            "PageBreak",
            "Paragraph",
        ]

    def test_level_without_a_known_page_gets_no_page_break(self):
        chapter = _chapter(_paragraph(("First.", PAGE_IV)), layout=None)
        document = _document(chapter)
        # The first page is the one of the first paragraph: the page break stands
        # inside the chapter, after its header.
        assert _kinds(document) == ["TopLevelChapterOfParagraphs"]
        assert _kinds(chapter) == ["PageBreak", "Paragraph"]

    def test_paragraph_without_sentences_and_table_without_rows_leave_the_page_alone(
        self,
    ):
        empty_paragraph = Paragraph(PAGE_V)
        empty_table = Table(PAGE_SIX, "empty", None, True, [])
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV)),
            empty_paragraph,
            empty_table,
            _paragraph(("Second.", PAGE_V)),
        )
        _document(chapter)
        assert _kinds(chapter) == [
            "Paragraph",
            "Paragraph",
            "Table",
            "PageBreak",
            "Paragraph",
        ]

    def test_inserting_twice_gives_the_same_document(self):
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV), ("Second.", PAGE_V)),
            _paragraph(("Third.", PAGE_SIX)),
        )
        document = _document(chapter)
        before = (_kinds(document), _kinds(chapter), _kinds(chapter.sublevels[0]))
        PageBreakInserter().insert_page_breaks(document)
        assert (
            _kinds(document),
            _kinds(chapter),
            _kinds(chapter.sublevels[0]),
        ) == before


class TestOrderOfThePages:
    """The pages of the page breaks strictly increase, or the order of the
    document is not the one of its pages."""

    def _oscillating_chapter(self):
        # 198, 199, 198, 199: a text of the page 198 stands after one of the 199
        return _chapter(
            _paragraph(("First.", PAGE_IV)),
            _paragraph(("Second.", PAGE_V)),
            _paragraph(("Third.", PAGE_IV)),
            _paragraph(("Fourth.", PAGE_V)),
        )

    def test_pages_in_order_are_not_reported(self):
        inserter = PageBreakInserter(strict=True)
        document = Document("Test")
        document.add_chapter(
            _chapter(_paragraph(("First.", PAGE_IV)), _paragraph(("Second.", PAGE_V)))
        )
        inserter.insert_page_breaks(document)
        assert inserter.violations == []

    def test_a_page_that_comes_back_is_reported_with_its_context(self):
        document = Document("Test")
        document.add_chapter(self._oscillating_chapter())
        inserter = PageBreakInserter()
        inserter.insert_page_breaks(document)
        assert len(inserter.violations) == 1
        assert "pdf page 4" in inserter.violations[0]
        assert "pdf page 5" in inserter.violations[0]
        assert "before Paragraph" in inserter.violations[0]

    def test_a_violation_is_warned_about(self, caplog):
        document = Document("Test")
        document.add_chapter(self._oscillating_chapter())
        with caplog.at_level("WARNING", logger="pdf_to_markdown"):
            PageBreakInserter().insert_page_breaks(document)
        assert "the pages are not in order" in caplog.text

    def test_a_violation_is_an_error_when_strict(self):
        document = Document("Test")
        document.add_chapter(self._oscillating_chapter())
        with pytest.raises(ConverterError, match="the pages are not in order"):
            PageBreakInserter(strict=True).insert_page_breaks(document)

    def test_a_page_break_within_a_paragraph_is_checked_too(self):
        document = Document("Test")
        document.add_chapter(
            _chapter(_paragraph(("First.", PAGE_V), ("Second.", PAGE_IV)))
        )
        inserter = PageBreakInserter()
        inserter.insert_page_breaks(document)
        assert len(inserter.violations) == 1
        assert "inside a paragraph" in inserter.violations[0]


class TestMarkersOfTheLevelsAndTheLeaves:
    def test_nothing_is_written_unless_asked_for(self):
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV)), _paragraph(("Second.", PAGE_V))
        )
        assert "<!--" not in "\n".join(_lines(chapter, page_markers=False))

    def test_marker_before_the_first_header_then_at_each_change_of_page(self):
        chapter = _chapter(
            _paragraph(("First paragraph.", PAGE_IV)),
            _paragraph(("Second paragraph.", PAGE_V)),
            _paragraph(("Third paragraph.", PAGE_V)),
        )
        assert _lines(chapter) == [
            "<!-- page reader=iv pdf=4 -->",
            "",
            "## Chapter",
            "",
            "First paragraph.",
            "",
            "<!-- page reader=v pdf=5 -->",
            "",
            "Second paragraph.",
            "",
            "Third paragraph.",
        ]

    def test_without_the_markers_the_markdown_is_the_one_of_a_document_without_page_breaks(
        self,
    ):
        def chapter():
            return _chapter(
                _paragraph(("First.", PAGE_IV), ("Second.", PAGE_V)),
                _paragraph(("Third.", PAGE_SIX)),
            )

        with_page_breaks = _lines(chapter(), page_markers=False)
        document = Document("Test")
        document.add_chapter(chapter())
        md_file = MdUtils(file_name="unused")
        DocumentHierarchicalLevel.write_sublevels_to_markdown(
            md_file, document.get_chapters_with_page_breaks(), 2, False
        )
        assert with_page_breaks == md_file.file_data_text.strip("\n").split("\n")

    def test_marker_inside_a_paragraph_is_a_line_of_its_own(self):
        chapter = _chapter(_paragraph(("First.", PAGE_IV), ("Second.", PAGE_V)))
        assert _lines(chapter)[-3:] == [
            "First.",
            "<!-- page reader=v pdf=5 -->",
            "Second.",
        ]

    def test_paragraph_merged_across_two_pages_is_marked_where_the_page_changes(self):
        # What ParagraphMerger leaves: the sentence cut by the page break keeps
        # the page where it starts, the next sentence is on the next page.
        chapter = _chapter(
            _paragraph(
                ("Many minds work.", PAGE_IV),
                ("The conscious mind lets them cooperate.", PAGE_IV),
                ("It is calm.", PAGE_V),
            )
        )
        assert _lines(chapter)[-3:] == [
            "Many minds work. The conscious mind lets them cooperate.",
            "<!-- page reader=v pdf=5 -->",
            "It is calm.",
        ]

    def test_blockquote_keeps_its_marker_outside_and_its_lines_inside(self):
        chapter = _chapter(
            _paragraph(("Running text.", PAGE_IV)),
            _paragraph(
                ("A quote.", PAGE_V),
                ("Goes on.", PAGE_SIX),
                paragraph_class=BlockQuoteParagraph,
            ),
        )
        assert _lines(chapter)[-5:] == [
            "<!-- page reader=v pdf=5 -->",
            "",
            "> A quote.",
            "> <!-- page reader=6 pdf=6 -->",
            "> Goes on.",
        ]

    def test_heading_is_preceded_by_the_marker_of_its_page(self):
        chapter = _chapter(
            _paragraph(("Before.", PAGE_IV)),
            Heading(PAGE_V, "A Title"),
            _paragraph(("After.", PAGE_V)),
        )
        assert _lines(chapter)[-5:] == [
            "<!-- page reader=v pdf=5 -->",
            "",
            "### A Title",
            "",
            "After.",
        ]

    def test_marker_goes_before_a_table_never_between_its_rows(self):
        table = Table(PAGE_V, "a table", None, True, [["H1", "H2"], ["a", "b"]])
        chapter = _chapter(_paragraph(("Before.", PAGE_IV)), table)
        assert _lines(chapter)[-5:] == [
            "<!-- page reader=v pdf=5 -->",
            "",
            "| H1 | H2 |",
            "| --- | --- |",
            "| a | b |",
        ]

    def test_level_without_a_known_page_gets_no_marker(self):
        chapter = _chapter(_paragraph(("First.", PAGE_IV)), layout=None)
        assert _lines(chapter)[:2] == ["## Chapter", ""]

    def test_marker_before_a_sub_chapter_is_before_its_header(self):
        sub_chapter = TopLevelChapterOfParagraphs("Sub chapter")
        sub_chapter.page_layout = PAGE_V
        sub_chapter.add_sublevel(_paragraph(("Deep text.", PAGE_V)))
        sub_chapter.renumber_sublevels()
        chapter = _chapter(_paragraph(("Before.", PAGE_IV)), sub_chapter)
        lines = _lines(chapter)
        assert lines[lines.index("<!-- page reader=v pdf=5 -->") + 2] == (
            "### Sub chapter"
        )


class TestLevelNamedOnThePageBeforeItsText:
    def test_the_header_has_the_marker_of_its_page_and_the_text_that_of_its_own(self):
        # A name that ends a page, the text it names starting on the next one
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV)),
            layout=PAGE_IV,
        )
        sub_chapter = TopLevelChapterOfParagraphs("Named at the end of a page")
        sub_chapter.page_layout = PAGE_IV
        sub_chapter.add_sublevel(_paragraph(("Its text.", PAGE_V)))
        sub_chapter.renumber_sublevels()
        chapter.add_sublevel(sub_chapter)
        chapter.renumber_sublevels()
        assert _lines(chapter) == [
            "<!-- page reader=iv pdf=4 -->",
            "",
            "## Chapter",
            "",
            "First.",
            "",
            "### Named at the end of a page",
            "",
            "<!-- page reader=v pdf=5 -->",
            "",
            "Its text.",
        ]


class TestMarkersInWrappedLines:
    SENTENCES = [
        ("Alpha alpha alpha alpha.", PAGE_IV),
        ("Beta beta beta beta beta.", PAGE_IV),
        ("Gamma gamma gamma gamma.", PAGE_V),
        ("Delta delta delta delta delta.", PAGE_V),
        ("Epsilon epsilon epsilon.", PAGE_SIX),
    ]

    def _paragraph_lines(self, page_markers, maximum_line_length):
        chapter = _chapter(_paragraph(*self.SENTENCES))
        lines = _lines(chapter, page_markers, maximum_line_length)
        return lines[lines.index("## Chapter") + 2 :]

    def test_a_marker_is_a_line_of_its_own(self):
        for maximum_line_length in (None, 30, 45, 60, 80, 120):
            lines = self._paragraph_lines(True, maximum_line_length)
            marker_lines = [line for line in lines if "<!-- page" in line]
            assert len(marker_lines) == 2
            assert all(MARKER_LINE.fullmatch(line) for line in marker_lines), lines

    def test_without_the_markers_the_words_are_the_ones_of_the_unmarked_markdown(self):
        for maximum_line_length in (None, 45, 80):
            marked = [
                line
                for line in self._paragraph_lines(True, maximum_line_length)
                if "<!-- page" not in line
            ]
            unmarked = self._paragraph_lines(False, maximum_line_length)
            assert " ".join(marked).split() == " ".join(unmarked).split()

    def test_the_wrapped_lines_resume_after_the_marker(self):
        chapter = _chapter(
            _paragraph(
                ("Alpha alpha alpha alpha.", PAGE_IV),
                ("Beta beta beta beta beta.", PAGE_IV),
                ("Gamma gamma gamma gamma.", PAGE_V),
                ("Delta delta delta delta delta.", PAGE_V),
            )
        )
        lines = _lines(chapter, maximum_line_length=50)
        assert lines[-4:] == [
            "Alpha alpha alpha alpha. Beta beta beta beta beta.",
            "<!-- page reader=v pdf=5 -->",
            "Gamma gamma gamma gamma.",
            "Delta delta delta delta delta.",
        ]


class TestMarkersInsideParagraphs:
    """A marker within a paragraph is a line of its own: a single newline on both
    sides, never a blank line (no new paragraph)."""

    def test_paragraph_count_is_the_one_of_the_unmarked_markdown(self):
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV), ("Second.", PAGE_V), ("Third.", PAGE_SIX))
        )
        marked = "\n".join(_lines(chapter))
        unmarked = "\n".join(_lines(chapter, page_markers=False))
        assert marked.count("\n\n") == unmarked.count("\n\n") + 1  # the first marker

    def test_blockquote_marker_line_keeps_the_quote_prefix(self):
        chapter = _chapter(
            _paragraph(
                ("A quote.", PAGE_IV),
                ("Goes on.", PAGE_SIX),
                paragraph_class=BlockQuoteParagraph,
            ),
        )
        assert _lines(chapter)[-3:] == [
            "> A quote.",
            "> <!-- page reader=6 pdf=6 -->",
            "> Goes on.",
        ]

    def test_marker_inside_a_list_item_is_at_the_column_of_its_content(self):
        chapter = _chapter(
            _paragraph(("1. Zero.", PAGE_IV)),
            _paragraph(("2. First.", PAGE_IV), ("Second.", PAGE_V)),
        )
        assert _lines(chapter)[-3:] == [
            "2. First.",
            "   <!-- page reader=v pdf=5 -->",
            "   Second.",
        ]


class TestMarkersInNumberedLists:
    def test_marker_before_an_item_belongs_to_the_previous_item(self):
        # A marker at the column of the item would end the list above: the
        # item would start a new list (markdownlint MD029).
        chapter = _chapter(
            _paragraph(("1. First item.", PAGE_IV)),
            _paragraph(("2. Second item.", PAGE_V)),
        )
        assert _lines(chapter)[-5:] == [
            "1. First item.",
            "",
            "   <!-- page reader=v pdf=5 -->",
            "",
            "2. Second item.",
        ]

    def test_marker_before_the_first_item_is_at_the_column_of_the_item(self):
        chapter = _chapter(
            _paragraph(("Running text.", PAGE_IV)),
            _paragraph(("1. First item.", PAGE_V)),
        )
        assert _lines(chapter)[-3:] == [
            "<!-- page reader=v pdf=5 -->",
            "",
            "1. First item.",
        ]

    def test_a_list_goes_on_across_a_page_break(self):
        # The page break between the items is transparent for the heuristic:
        # the second item is still the second item of the list.
        chapter = _chapter(
            _paragraph(("1. First item.", PAGE_IV)),
            _paragraph(("2. Second item.", PAGE_V)),
            _paragraph(("3. Third item.", PAGE_V)),
        )
        assert _lines(chapter)[-3:] == [
            "2. Second item.",
            "",
            "3. Third item.",
        ]

    @pytest.mark.parametrize(
        "text,role,indentation,expected",
        [
            ("2. Item", NumberedListRole.ITEM, 0, 3),
            ("10. Item", NumberedListRole.ITEM, 0, 3),
            ("11. Item", NumberedListRole.ITEM, 0, 4),
            ("2. Nested item", NumberedListRole.ITEM, 3, 6),
            ("1. First item", NumberedListRole.ITEM, 0, 0),
            ("1. First nested item", NumberedListRole.ITEM, 3, 3),
            ("A paragraph of the item above.", NumberedListRole.CONTINUATION, 3, 3),
            ("A paragraph.", NumberedListRole.NONE, 0, 0),
            ("2. Failed", NumberedListRole.FAILED, 0, 0),
        ],
    )
    def test_indentation_of_a_comment_before_a_paragraph(
        self, text, role, indentation, expected
    ):
        placement = NumberedListPlacement(role, indentation)
        assert (
            NumberedListAnnotator.indentation_of_comment_before(text, placement)
            == expected
        )


class TestDocumentToMarkdown:
    def _document(self):
        chapter = _chapter(_paragraph(("Only sentence.", PAGE_IV)))
        return _document(chapter)

    def test_markers_are_written_when_asked_for(self, tmp_path):
        path = tmp_path / "with_markers.md"
        self._document().to_markdown(str(path), page_markers=True)
        assert "<!-- page reader=iv pdf=4 -->" in path.read_text()

    def test_markers_are_not_written_by_default(self, tmp_path):
        path = tmp_path / "without_markers.md"
        self._document().to_markdown(str(path))
        assert "<!--" not in path.read_text()

    def test_debug_comments_switch_the_markers_on(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDF_TO_MARKDOWN_DEBUG_COMMENTS", "1")
        path = tmp_path / "debug_comments.md"
        self._document().to_markdown(str(path))
        assert "<!-- page reader=iv pdf=4 -->" in path.read_text()

    def test_a_document_without_pages_gets_no_markers_from_the_debug_comments(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("PDF_TO_MARKDOWN_DEBUG_COMMENTS", "1")
        document = self._document()
        document.knows_pages = False
        path = tmp_path / "no_pages.md"
        document.to_markdown(str(path))
        assert "<!--" not in path.read_text()

    def test_a_document_without_page_breaks_gets_no_markers(self, tmp_path):
        document = Document("Test")
        document.add_chapter(_chapter(_paragraph(("Only sentence.", PAGE_IV))))
        path = tmp_path / "no_page_breaks.md"
        document.to_markdown(str(path), page_markers=True)
        assert "<!--" not in path.read_text()

    def test_a_document_read_from_markdown_knows_no_pages(self, tmp_path):
        from pdf_to_markdown import MarkdownToDocument

        source = tmp_path / "source.md"
        source.write_text("# Title\n\n## Chapter\n\nFirst sentence. Second one.\n")
        assert MarkdownToDocument(str(source)).get_document().knows_pages is False

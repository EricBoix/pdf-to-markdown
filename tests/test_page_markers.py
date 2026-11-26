"""PageMarker: where the sentences come from, written in the markdown."""

import re

import pytest
from mdutils.mdutils import MdUtils

from pdf_to_markdown import (
    BlockQuoteParagraph,
    Document,
    Heading,
    PageLayout,
    PageMarker,
    PageMarkerTracker,
    Paragraph,
    Sentence,
    Table,
    TopLevelChapterOfParagraphs,
)
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

INLINE_MARKER = re.compile(r" <!-- page reader=\S+ pdf=\d+ -->")


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


# (inline markers by default here: the tests of the default are explicit)
def _lines(chapter, page_markers=True, maximum_line_length=None, on_own_line=False):
    """The markdown of a chapter, as lines (the blank lines kept)."""
    document = Document("Test")
    document.add_chapter(chapter)
    document.maximum_line_length = maximum_line_length
    md_file = MdUtils(file_name="unused")
    chapter.to_markdown(
        md_file,
        level=2,
        page_markers=PageMarkerTracker(on_own_line) if page_markers else None,
    )
    return md_file.file_data_text.strip("\n").split("\n")


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


class TestPageMarkerTracker:
    def test_first_text_gets_a_marker_then_only_changes_of_page(self):
        tracker = PageMarkerTracker()
        assert tracker.comment_for(PAGE_IV) == "<!-- page reader=iv pdf=4 -->"
        assert tracker.comment_for(PAGE_IV) is None
        assert tracker.comment_for(PAGE_V) == "<!-- page reader=v pdf=5 -->"
        assert tracker.comment_for(PAGE_V) is None

    def test_going_back_to_a_page_is_a_change(self):
        tracker = PageMarkerTracker()
        tracker.comment_for(PAGE_IV)
        tracker.comment_for(PAGE_V)
        assert tracker.comment_for(PAGE_IV) is not None

    def test_unknown_layout_leaves_the_current_page_alone(self):
        tracker = PageMarkerTracker()
        tracker.comment_for(PAGE_IV)
        assert tracker.comment_for(None) is None
        assert tracker.comment_for(PAGE_IV) is None


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

    def test_marker_inside_a_paragraph_sticks_to_the_previous_sentence(self):
        chapter = _chapter(_paragraph(("First.", PAGE_IV), ("Second.", PAGE_V)))
        assert _lines(chapter)[-1] == "First. <!-- page reader=v pdf=5 --> Second."

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
        assert _lines(chapter)[-1] == (
            "Many minds work. The conscious mind lets them cooperate. "
            "<!-- page reader=v pdf=5 --> It is calm."
        )

    def test_blockquote_keeps_its_marker_outside_and_its_lines_inside(self):
        chapter = _chapter(
            _paragraph(("Running text.", PAGE_IV)),
            _paragraph(
                ("A quote.", PAGE_V),
                ("Goes on.", PAGE_SIX),
                paragraph_class=BlockQuoteParagraph,
            ),
        )
        assert _lines(chapter)[-3:] == [
            "<!-- page reader=v pdf=5 -->",
            "",
            "> A quote. <!-- page reader=6 pdf=6 --> Goes on.",
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

    def test_a_marker_never_starts_a_line(self):
        for maximum_line_length in (30, 45, 60, 80, 120):
            lines = self._paragraph_lines(True, maximum_line_length)
            assert not any(line.startswith("<!--") for line in lines), lines
            assert sum(line.count("<!-- page") for line in lines) == 2

    def test_lines_stay_within_the_limit_while_markers_stick_to_a_word(self):
        for line in self._paragraph_lines(True, 60):
            assert len(line) <= 60 + len("<!-- page reader=6 pdf=6 -->")

    def test_without_the_markers_the_text_is_the_one_of_the_unmarked_markdown(self):
        for maximum_line_length in (None, 45, 80):
            marked = " ".join(self._paragraph_lines(True, maximum_line_length))
            unmarked = " ".join(self._paragraph_lines(False, maximum_line_length))
            assert INLINE_MARKER.sub("", marked).split() == unmarked.split()

    def test_unlimited_line_is_the_unmarked_one_with_markers_inserted(self):
        marked = self._paragraph_lines(True, None)[0]
        unmarked = self._paragraph_lines(False, None)[0]
        assert INLINE_MARKER.sub("", marked) == unmarked


class TestMarkersOnTheirOwnLine:
    """With on_own_line a marker within a paragraph is a line of its own: a
    single newline on both sides, never a blank line (no new paragraph)."""

    def test_marker_inside_a_paragraph_is_a_line_of_its_own(self):
        chapter = _chapter(_paragraph(("First.", PAGE_IV), ("Second.", PAGE_V)))
        assert _lines(chapter, on_own_line=True)[-3:] == [
            "First.",
            "<!-- page reader=v pdf=5 -->",
            "Second.",
        ]

    def test_paragraph_count_is_the_one_of_the_inline_markers(self):
        chapter = _chapter(
            _paragraph(("First.", PAGE_IV), ("Second.", PAGE_V), ("Third.", PAGE_SIX))
        )
        inline = "\n".join(_lines(chapter))
        on_own_line = "\n".join(_lines(chapter, on_own_line=True))
        assert inline.count("\n\n") == on_own_line.count("\n\n")
        assert inline.split() == on_own_line.split()

    def test_the_wrapped_lines_resume_after_the_marker(self):
        chapter = _chapter(
            _paragraph(
                ("Alpha alpha alpha alpha.", PAGE_IV),
                ("Beta beta beta beta beta.", PAGE_IV),
                ("Gamma gamma gamma gamma.", PAGE_V),
                ("Delta delta delta delta delta.", PAGE_V),
            )
        )
        lines = _lines(chapter, maximum_line_length=50, on_own_line=True)
        assert lines[-4:] == [
            "Alpha alpha alpha alpha. Beta beta beta beta beta.",
            "<!-- page reader=v pdf=5 -->",
            "Gamma gamma gamma gamma.",
            "Delta delta delta delta delta.",
        ]

    def test_blockquote_marker_line_keeps_the_quote_prefix(self):
        chapter = _chapter(
            _paragraph(
                ("A quote.", PAGE_IV),
                ("Goes on.", PAGE_SIX),
                paragraph_class=BlockQuoteParagraph,
            ),
        )
        assert _lines(chapter, on_own_line=True)[-3:] == [
            "> A quote.",
            "> <!-- page reader=6 pdf=6 -->",
            "> Goes on.",
        ]

    def test_marker_inside_a_list_item_is_at_the_column_of_its_content(self):
        chapter = _chapter(
            _paragraph(("1. Zero.", PAGE_IV)),
            _paragraph(("2. First.", PAGE_IV), ("Second.", PAGE_V)),
        )
        assert _lines(chapter, on_own_line=True)[-3:] == [
            "2. First.",
            "   <!-- page reader=v pdf=5 -->",
            "   Second.",
        ]

    def test_on_their_own_line_by_default(self):
        assert PageMarkerTracker().on_own_line
        assert not PageMarkerTracker(on_own_line=False).on_own_line


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
        document = Document("Test")
        document.add_chapter(chapter)
        return document

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

    def test_a_document_read_from_markdown_knows_no_pages(self, tmp_path):
        from pdf_to_markdown import MarkdownToDocument

        source = tmp_path / "source.md"
        source.write_text("# Title\n\n## Chapter\n\nFirst sentence. Second one.\n")
        assert MarkdownToDocument(str(source)).get_document().knows_pages is False

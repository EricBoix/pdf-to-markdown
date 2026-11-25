"""Tests for the tables: extraction from the layout text, splitting, markdown.

The layout text used here is modelled on the pages of a real book: a free-form
table (one row per line, empty cells) and a captioned table whose rows are
separated by blank lines and that spreads over two pages, a row being cut by
the page break.
"""

from mdutils.mdutils import MdUtils

from pdf_to_markdown import (
    ExtractedPage,
    PageLayout,
    NumberedListPlacement,
    NumberedListRole,
    Paragraph,
    ParagraphAndBlockquoteSplitter,
    ParagraphMerger,
    Sentence,
    SpanningCellText,
    StructuralInfoBase,
    Table,
    TableDeclaration,
    TableExtractor,
    TableRegistry,
    TableLayoutParser,
    TablePlaceholder,
    TableText,
    TopLevelChapterOfParagraphs,
)

FREE_FORM_PAGE = (
    "Here is how the two models align:\n"
    "\n"
    "    CULADASA" + " " * 57 + "ASANGA\n"
    " 1. Establishing a Practice\n"
    " 2. Interrupted Attention"
    + " " * 34
    + "1. Stoppage (sthaapaya)\n"
    + " " * 66
    + "2. Continual Stoppage (samsthaapaya)\n"
    " 3. Extended Attention" + " " * 37 + "3. Restorative Stoppage\n"
    "\n"
    "Asanga's sthaapaya (1) is included in my Stage Two.\n"
)


def hindrance_line(first_column="", second_column="", third_column=""):
    """A line of the layout text of the hindrances table: the columns start at
    the positions 3, 37 and 80 (as the gutters of a real page are wide)."""
    return (
        " " * 3 + first_column.ljust(34) + second_column.ljust(43) + third_column
    ).rstrip()


HINDRANCES_FIRST_PAGE = "\n".join(
    [
        "Some running text.",
        "",
        "                    TABLE 4. THE FIVE HINDRANCES",
        "",
        hindrance_line("Hindrance", "Explanation", "Opposing Factor"),
        "",
        hindrance_line("", "Pursuit of pleasures", "Unification of Mind: A"),
        hindrance_line(
            "WORLDLY DESIRE",
            "to our material existence.",
            "unified mind has no reason.",
        ),
        "",
        hindrance_line("", "Remorse for unwise,", "Meditative joy: Joy"),
        hindrance_line(
            "", "illegal activities. Worry about", "produces confidence and"
        ),
        "",
    ]
)

HINDRANCES_SECOND_PAGE = "\n".join(
    [
        hindrance_line(
            "AGITATION DUE TO", "consequences for past", "optimism. Joy overcomes"
        ),
        hindrance_line("REMORSE AND WORRY", "actions.", "remorse."),
        "",
        hindrance_line("", "A biased mental process.", "Sustained Attention: Success."),
        hindrance_line("DOUBT", "Self-doubt saps our will.", "Doubt disappears."),
        " * This is a two-way street.",
        "",
        "Running text again.",
        "",
    ]
)


class StructuralInfoWithTables(StructuralInfoBase):
    def __init__(self, declarations, pages_info=None):
        StructuralInfoBase.__init__(self)
        self._declarations = declarations
        # What the tests give to their TableExtractor and read the tables from
        self.table_registry = TableRegistry()
        self._pages_info = pages_info or {}

    @property
    def pages_info(self) -> dict:
        return self._pages_info

    @property
    def total_page_number(self) -> int:
        return 3

    @property
    def table_declarations(self):
        return self._declarations


def free_form_declaration():
    return TableDeclaration(
        "free form",
        r"^(?= *CULADASA {5,}ASANGA)",
        column_count=2,
        end_pattern=r"^Asanga's sthaapaya",
    )


def hindrances_declaration():
    return TableDeclaration(
        "TABLE 4",
        r"^ *(?P<caption>TABLE 4\. THE FIVE HINDRANCES)\n",
        column_count=3,
        end_pattern=r"^ \* This is a two-way street",
        row_strategy=TableDeclaration.ROW_PER_BLANK_LINE,
    )


def make_page(page_number, text, removed_first_line_indentation=0):
    page = ExtractedPage(page_number, PageLayout(str(page_number), page_number), None)
    page.set_text(text)
    page.removed_first_line_indentation = removed_first_line_indentation
    return page


class TestTableLayoutParser:
    def test_one_row_per_line_with_empty_cells(self):
        rows = TableLayoutParser().parse(
            FREE_FORM_PAGE.split("\n\n", 1)[1], free_form_declaration()
        )
        assert rows[0] == ["CULADASA", "ASANGA"]
        assert rows[1] == ["1. Establishing a Practice", ""]
        assert rows[2] == ["2. Interrupted Attention", "1. Stoppage (sthaapaya)"]
        assert rows[3] == ["", "2. Continual Stoppage (samsthaapaya)"]

    def test_rows_separated_by_blank_lines_have_their_wrapped_cells_joined(self):
        text = (
            "Hindrance         Explanation\n"
            "\n"
            "                  Pursuit of pleasures fame-\n"
            "WORLDLY DESIRE    obscurity; praise-blame.\n"
        )
        declaration = TableDeclaration(
            "t",
            "^",
            column_count=2,
            row_strategy=TableDeclaration.ROW_PER_BLANK_LINE,
        )
        rows = TableLayoutParser().parse(text, declaration)
        assert rows == [
            ["Hindrance", "Explanation"],
            ["WORLDLY DESIRE", "Pursuit of pleasures fame-obscurity; praise-blame."],
        ]


class TestTableExtractor:
    def test_nothing_is_done_without_declared_table(self):
        extractor = TableExtractor(StructuralInfoWithTables([]), TableRegistry())
        page = make_page(1, FREE_FORM_PAGE)
        extractor.extract_tables(page)
        assert page.text == FREE_FORM_PAGE

    def test_table_is_replaced_by_a_placeholder_and_kept_in_the_registry(self):
        structural_info = StructuralInfoWithTables([free_form_declaration()])
        extractor = TableExtractor(structural_info, structural_info.table_registry)
        page = make_page(1, FREE_FORM_PAGE)
        extractor.extract_tables(page)
        assert page.text == (
            "Here is how the two models align:\n"
            "\n"
            + TablePlaceholder.make("free form")
            + "\n"
            + "Asanga's sthaapaya (1) is included in my Stage Two.\n"
        )
        content = structural_info.table_registry.get("free form")
        assert content.caption is None
        assert content.rows[0] == ["CULADASA", "ASANGA"]
        assert len(content.rows) == 5

    def test_captioned_table_spreading_over_two_pages_is_one_table(self):
        structural_info = StructuralInfoWithTables(
            [hindrances_declaration()],
            {2: {}},
        )
        extractor = TableExtractor(structural_info, structural_info.table_registry)
        first_page = make_page(1, HINDRANCES_FIRST_PAGE)
        second_page = make_page(2, HINDRANCES_SECOND_PAGE)
        extractor.extract_tables(first_page)
        extractor.extract_tables(second_page)
        extractor.check_all_tables_closed()

        assert first_page.text == (
            "Some running text.\n\n" + TablePlaceholder.make("TABLE 4") + "\n"
        )
        # What follows the table keeps the newline that ended its last line
        assert second_page.text.startswith("\n * This is a two-way street.")
        content = structural_info.table_registry.get("TABLE 4")
        assert content.caption == "TABLE 4. THE FIVE HINDRANCES"
        assert [row[0] for row in content.rows] == [
            "Hindrance",
            "WORLDLY DESIRE",
            # The row cut by the page break was glued back together
            "AGITATION DUE TO REMORSE AND WORRY",
            "DOUBT",
        ]
        assert content.rows[2][1] == (
            "Remorse for unwise, illegal activities. Worry about "
            "consequences for past actions."
        )

    def test_row_cut_by_page_break_follows_the_declaration_when_there_is_one(self):
        structural_info = StructuralInfoWithTables(
            [hindrances_declaration()],
            {2: {StructuralInfoBase.KEY_TABLE_ROW_CONTINUES: False}},
        )
        extractor = TableExtractor(structural_info, structural_info.table_registry)
        extractor.extract_tables(make_page(1, HINDRANCES_FIRST_PAGE))
        extractor.extract_tables(make_page(2, HINDRANCES_SECOND_PAGE))
        content = structural_info.table_registry.get("TABLE 4")
        assert len(content.rows) == 5

    def test_first_line_indentation_removed_by_the_extraction_is_restored(self):
        structural_info = StructuralInfoWithTables([hindrances_declaration()])
        extractor = TableExtractor(structural_info, structural_info.table_registry)
        extractor.extract_tables(make_page(1, HINDRANCES_FIRST_PAGE))
        stripped_text = HINDRANCES_SECOND_PAGE.lstrip()
        extractor.extract_tables(make_page(2, stripped_text, 3))
        content = structural_info.table_registry.get("TABLE 4")
        assert content.rows[2][0] == "AGITATION DUE TO REMORSE AND WORRY"

    def test_unclosed_table_is_reported(self, caplog):
        structural_info = StructuralInfoWithTables([hindrances_declaration()])
        extractor = TableExtractor(structural_info, structural_info.table_registry)
        extractor.extract_tables(make_page(1, HINDRANCES_FIRST_PAGE))
        with caplog.at_level("WARNING", logger="pdf_to_markdown"):
            extractor.check_all_tables_closed()
        assert "never closed" in caplog.text


class TestTableSplitting:
    def test_placeholder_becomes_a_table_part_between_paragraphs(self):
        splitter = ParagraphAndBlockquoteSplitter("\n   ", r"(?!x)x")
        text = (
            "   First paragraph.\n"
            + TablePlaceholder.make("TABLE 4")
            + "\n   Second paragraph.\n"
        )
        parts = splitter.split(text)
        assert [splitter.is_table(part) for part in parts] == [False, True, False]
        assert parts[1] == "TABLE 4"
        assert isinstance(parts[1], TableText)

    def test_text_without_placeholder_holds_no_table(self):
        splitter = ParagraphAndBlockquoteSplitter("\n   ", r"(?!x)x")
        parts = splitter.split("   Only a paragraph.\n")
        assert not any(splitter.is_table(part) for part in parts)


class TestTableMarkdown:
    def _markdown_of(self, table):
        md_file = MdUtils(file_name="unused")
        table.to_markdown(md_file, 3)
        return md_file.file_data_text

    def test_table_with_column_headings_has_its_caption_above(self):
        table = Table(
            PageLayout("1", 1),
            "TABLE 4",
            "TABLE 4. THE FIVE HINDRANCES",
            True,
            [["Hindrance", "Explanation"], ["DOUBT", "A | B"]],
        )
        assert self._markdown_of(table).strip("\n").split("\n") == [
            "TABLE 4. THE FIVE HINDRANCES",
            "",
            "| Hindrance | Explanation |",
            "| --- | --- |",
            "| DOUBT | A \\| B |",
        ]

    def test_empty_cell_is_a_single_whitespace_between_pipes(self):
        table = Table(
            PageLayout("1", 1),
            "t",
            None,
            True,
            [["A", "B"], ["1. One", ""], ["", "2. Two"]],
        )
        assert self._markdown_of(table).strip("\n").split("\n") == [
            "| A | B |",
            "| --- | --- |",
            "| 1. One | |",
            "| | 2. Two |",
        ]

    def test_table_inside_a_list_item_is_indented_with_the_item(self):
        table = Table(
            PageLayout("1", 1),
            "t",
            "A caption",
            True,
            [["A", "B"], ["1", "2"]],
        )
        table.numbered_list_placement = NumberedListPlacement(
            NumberedListRole.CONTINUATION, 3
        )
        assert self._markdown_of(table).strip("\n").split("\n") == [
            "   A caption",
            "",
            "   | A | B |",
            "   | --- | --- |",
            "   | 1 | 2 |",
        ]

    def test_caption_takes_the_header_row_of_a_table_without_column_headings(self):
        table = Table(
            PageLayout("1", 1),
            "TABLE 1",
            "TABLE 1. THE TEN STAGES",
            False,
            [["THE NOVICE", "Stage One"]],
        )
        assert self._markdown_of(table).strip("\n").split("\n") == [
            "| TABLE 1. THE TEN STAGES | ──────────────── |",
            "| --- | --- |",
            "| THE NOVICE | Stage One |",
        ]


class _MergerStructuralInfo(StructuralInfoBase):
    """What ParagraphMerger asks of a structural info, for a two pages chapter."""

    pages_info = {}
    total_page_number = 2
    numbered_list_heuristics_enabled = False

    def _get_page_number_finishing_last_paragraph(self, page_number):
        return page_number + 1

    def _holds_new_chapter(self, page_number):
        return False


class TestTableInterruptsTheTextFlow:
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
    def _paragraph(page_number, sentence_text):
        paragraph = Paragraph(PageLayout(page_number, page_number))
        paragraph.add_sublevel(
            Sentence(sentence_text, PageLayout(page_number, page_number))
        )
        paragraph.renumber_sublevels()
        return paragraph

    def test_paragraph_cut_by_a_page_break_is_merged_without_table(self):
        ending = self._paragraph(1, "Here is how the two models align:")
        starting = self._paragraph(2, "Asanga's stages are included in mine.")
        chapter = self._chapter_with(ending, starting)
        ParagraphMerger(
            _MergerStructuralInfo()
        ).reconstitute_paragraphs_spreading_over_two_pages(chapter)
        assert chapter.get_sublevels() == [ending]

    def test_paragraph_is_not_glued_to_the_one_following_a_table(self):
        ending = self._paragraph(1, "Here is how the two models align:")
        table = Table(PageLayout(1, 1), "t", None, True, [["A", "B"]])
        starting = self._paragraph(2, "Asanga's stages are included in mine.")
        chapter = self._chapter_with(ending, table, starting)
        ParagraphMerger(
            _MergerStructuralInfo()
        ).reconstitute_paragraphs_spreading_over_two_pages(chapter)
        assert chapter.get_sublevels() == [ending, table, starting]


STAGES_FIRST_PAGE = "\n".join(
    [
        "Some running text.",
        "",
        "               TABLE 1. THE TEN STAGES AND FOUR MILESTONES",
        "",
        "                            Stage One: Establishing a Practice",
        "      THE NOVICE            Stage Two: Interrupted Attention and Mind-Wandering",
        "      MEDITATOR",
        "                            Stage Three: Extended Attention and Forgetting",
        "",
        "                        Milestone One: Continuous Attention to the Object",
        "",
        "                            Stage Four: Continuous Attention and Overcoming Gross",
        "      THE SKILLED           Strong Dullness",
        "      MEDITATOR             Stage Five: Overcoming Subtle Dullness",
    ]
)

STAGES_SECOND_PAGE = "\n".join(
    [
        "                          Stage Six: Subduing Subtle Distraction",
        "                           Milestone Two: Sustained Exclusive Focus of Attention",
        "   THE TRANSITION         Stage Seven: Exclusive Attention and Unifying the Mind",
        "                              Milestone Three: Effortless Stability of Attention",
        "                          Stage Eight: Mental Pliancy and Pacifying the Senses",
        "      THE ADEPT           Stage Nine: Mental and Physical Pliancy and Calming the",
        "     MEDITATOR            Meditative Joy",
        "                          Stage Ten: Tranquility and Equanimity",
        "                       Milestone Four: Persistence of the Mental Qualities",
        "                       The Novice--Stages One through Three",
        "",
        "Running text again.",
    ]
)


def stages_declaration():
    return TableDeclaration(
        "TABLE 1",
        r"^ *(?P<caption>TABLE 1\. THE TEN STAGES AND FOUR MILESTONES) *(?:\n|\Z)",
        column_count=2,
        end_pattern=r"^ *The Novice--Stages One through Three",
        row_strategy=TableDeclaration.ROW_PER_PATTERN,
        has_column_headings=False,
        row_start_pattern=r"^Stage ",
        spanning_row_pattern=r"^Milestone ",
        first_column_spans_rows=True,
    )


class TestTableWithSpanningLabelsAndRows:
    def _read(self, caplog):
        structural_info = StructuralInfoWithTables([stages_declaration()])
        extractor = TableExtractor(structural_info, structural_info.table_registry)
        extractor.extract_tables(make_page(1, STAGES_FIRST_PAGE))
        extractor.extract_tables(make_page(2, STAGES_SECOND_PAGE.lstrip(), 26))
        extractor.check_all_tables_closed()
        return structural_info.table_registry.get("TABLE 1")

    def test_a_label_is_given_to_the_first_row_of_its_group(self, caplog):
        content = self._read(caplog)
        labelled_rows = [
            (row[0], row[1][:12]) for row in content.rows if row[0] and row[1]
        ]
        assert labelled_rows == [
            ("THE NOVICE MEDITATOR", "Stage One: E"),
            ("THE SKILLED MEDITATOR", "Stage Four: "),
            ("THE TRANSITION", "Stage Seven:"),
            ("THE ADEPT MEDITATOR", "Stage Eight:"),
        ]

    def test_milestones_are_rows_spanning_the_columns(self, caplog):
        content = self._read(caplog)
        spanning_rows = [
            row for row in content.rows if isinstance(row[0], SpanningCellText)
        ]
        assert [str(row[0])[:13] for row in spanning_rows] == [
            "Milestone One",
            "Milestone Two",
            "Milestone Thr",
            "Milestone Fou",
        ]

    def test_row_is_not_cut_by_the_page_break_and_wrapped_cells_are_joined(
        self, caplog
    ):
        content = self._read(caplog)
        stage_texts = [row[1] for row in content.rows if row[1].startswith("Stage ")]
        assert len(stage_texts) == 10
        assert (
            stage_texts[3]
            == "Stage Four: Continuous Attention and Overcoming Gross Strong Dullness"
        )
        assert stage_texts[5] == "Stage Six: Subduing Subtle Distraction"

    def test_markdown_of_a_spanning_row(self):
        table = Table(
            PageLayout("1", 1),
            "TABLE 1",
            "TABLE 1. STAGES",
            False,
            [
                ["THE NOVICE", "Stage One"],
                [SpanningCellText("Milestone One"), ""],
            ],
        )
        md_file = MdUtils(file_name="unused")
        table.to_markdown(md_file, 3)
        assert md_file.file_data_text.strip("\n").split("\n")[-1] == (
            "| **Milestone One** | ──────────────── |"
        )

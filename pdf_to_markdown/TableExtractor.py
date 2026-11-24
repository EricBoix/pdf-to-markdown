import re

from .DiagnosticsReporter import DiagnosticsReporter
from .TableDeclaration import TableDeclaration
from .TableLayoutParser import TableLayoutParser
from .TablePlaceholder import TablePlaceholder
from .TableRegistry import SpanningCellText, TableContent


class _OpenTable:
    """A table that was started on a page and is not finished yet."""

    def __init__(self, declaration: TableDeclaration, content: TableContent) -> None:
        self.declaration = declaration
        self.content = content


class TableExtractor:
    """Cuts the tables declared by the structural information out of the pages.

    The pages must be given in the order of the document. The text of a table
    is replaced, in the text of the page on which the table starts, by a
    TablePlaceholder line. The text of the table, on the pages it spreads
    over, is removed from the text of those pages. The cells of the table are
    kept in the TableRegistry of the structural information.

    Nothing is done (the text of the pages is left untouched) as long as the
    structural information does not declare tables.
    """

    def __init__(
        self, structural_info, diagnostics: DiagnosticsReporter | None = None
    ) -> None:
        self._structural_info = structural_info
        self._diagnostics = (
            diagnostics if diagnostics is not None else DiagnosticsReporter()
        )
        self._declarations = structural_info.table_declarations
        self._registry = structural_info.table_registry
        self._parser = TableLayoutParser(self._diagnostics)
        self._started_table_names: set[str] = set()
        self._open_table: _OpenTable | None = None

    def extract_tables(self, extracted_page) -> None:
        """Cut the tables out of the text of the given page (in place)."""
        if not self._declarations and self._open_table is None:
            return
        page_text = extracted_page.text
        if not page_text:
            return
        page_number = extracted_page.page_number
        missing_indentation = getattr(
            extracted_page, "removed_first_line_indentation", 0
        )

        kept_parts = []
        position = 0
        if self._open_table is not None:
            end_position = self._find_end(self._open_table.declaration, page_text, 0)
            region_end = len(page_text) if end_position is None else end_position
            self._append_fragment(
                self._open_table,
                self._restore_indentation(page_text[:region_end], missing_indentation),
                page_number,
            )
            if end_position is None:
                extracted_page.text = ""
                return
            self._open_table = None
            position = region_end
            # What follows the table was preceded by the lines of the table:
            # the newline ending the last of them is kept (a header, for
            # instance, is recognized by the newline preceding it).
            kept_parts.append("\n")

        while True:
            next_start = self._find_next_start(page_text, position, page_number)
            if next_start is None:
                break
            declaration, start_match = next_start
            kept_parts.append(page_text[position : start_match.start()])
            self._started_table_names.add(declaration.name)
            content = TableContent(
                declaration.name,
                self._get_caption(start_match),
                declaration.has_column_headings,
            )
            self._registry.add(content)
            kept_parts.append(TablePlaceholder.make(declaration.name) + "\n")

            body_start = start_match.end()
            end_position = self._find_end(declaration, page_text, body_start)
            region_end = len(page_text) if end_position is None else end_position
            region_text = page_text[body_start:region_end]
            if body_start == 0:
                region_text = self._restore_indentation(
                    region_text, missing_indentation
                )
            opened_table = _OpenTable(declaration, content)
            self._append_fragment(opened_table, region_text, page_number)
            position = region_end
            if end_position is None:
                # Without end pattern the table ends with its page, with one
                # it goes on until the page holding the end pattern.
                if declaration.end_pattern is not None:
                    self._open_table = opened_table
                break
        kept_parts.append(page_text[position:])
        extracted_page.text = "".join(kept_parts)

    def check_all_tables_closed(self) -> None:
        if self._open_table is not None:
            self._diagnostics.warn(
                f"Table {self._open_table.declaration.name!r} was never closed: "
                f"its end pattern was not found."
            )

    @staticmethod
    def _restore_indentation(region_text: str, missing_indentation: int) -> str:
        """Give back to the first line of a page the indentation that was stripped."""
        return " " * missing_indentation + region_text

    @staticmethod
    def _get_caption(start_match: re.Match[str]) -> str | None:
        if "caption" not in start_match.re.groupindex:
            return None
        caption = start_match.group("caption")
        if caption is None:
            return None
        return re.sub(r"\s+", " ", caption).strip()

    def _find_next_start(
        self, page_text: str, position: int, page_number: int
    ) -> tuple[TableDeclaration, re.Match[str]] | None:
        earliest = None
        for declaration in self._declarations:
            if declaration.name in self._started_table_names:
                continue
            if (
                declaration.start_page_number is not None
                and declaration.start_page_number != page_number
            ):
                continue
            match = declaration.start_pattern.search(page_text, position)
            if match is None:
                continue
            if earliest is None or match.start() < earliest[1].start():
                earliest = (declaration, match)
        return earliest

    @staticmethod
    def _find_end(
        declaration: TableDeclaration, page_text: str, from_position: int
    ) -> int | None:
        """Where the table stops in the page text, None when it does not."""
        if declaration.end_pattern is None:
            return None
        end_match = declaration.end_pattern.search(page_text, from_position)
        if end_match is None:
            return None
        return end_match.start()

    def _append_fragment(
        self, table: _OpenTable, fragment_text: str, page_number: int
    ) -> None:
        new_rows = self._parser.parse(fragment_text, table.declaration)
        if not new_rows:
            return
        content = table.content
        if not content.rows:
            content.rows.extend(new_rows)
            return
        # A table fragment starting a page continues the table of the previous
        # page: its first row is possibly the end of the last row of the
        # previous page.
        last_row = content.rows[-1]
        first_new_row = new_rows[0]
        row_continues, reason = self._decide_row_continuation(
            page_number, last_row, first_new_row
        )
        self._diagnostics.warn(
            f"Table {content.name!r}, page break before page {page_number}: row "
            f"{'merged' if row_continues else 'not merged'} ({reason})."
        )
        if row_continues:
            content.rows[-1] = [
                TableLayoutParser.join_wrapped_text([previous_cell, new_cell])
                for previous_cell, new_cell in zip(last_row, first_new_row)
            ]
            content.rows.extend(new_rows[1:])
        else:
            content.rows.extend(new_rows)

    def _decide_row_continuation(
        self, page_number: int, last_row: list[str], first_new_row: list[str]
    ) -> tuple[bool, str]:
        """Whether a row of a table was cut in two by a page break.

        The decision declared by the structural information wins. Otherwise a
        row is taken for cut when two signals come together: a cell is empty
        in the last row of the previous page while it holds text in the first
        row of the next page, and a cell of the first row of the next page
        starts with a lowercase letter (the text goes on).
        """
        if isinstance(last_row[0], SpanningCellText) or isinstance(
            first_new_row[0], SpanningCellText
        ):
            return False, "a row spanning all the columns is never cut"
        declared = self._structural_info.get_table_row_continues(page_number)
        if declared is not None:
            return declared, "declared in the structural information"
        complementary_cell = any(
            not previous_cell and new_cell
            for previous_cell, new_cell in zip(last_row, first_new_row)
        )
        lowercase_start = any(cell[:1].islower() for cell in first_new_row)
        if complementary_cell and lowercase_start:
            return True, "empty cell completed and lowercase start"
        return False, "no complementary empty cell or no lowercase start"

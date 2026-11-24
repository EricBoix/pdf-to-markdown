from .DiagnosticsReporter import DiagnosticsReporter
from .TableDeclaration import TableDeclaration
from .TableRegistry import SpanningCellText


class TableLayoutParser:
    """Reads the rows and cells of a table out of its layout text.

    The layout text keeps the horizontal position of the text of the pdf: the
    columns of a table are vertical strips separated by gutters, that is
    strips that are blank in every line of the table. The position of the
    columns is computed on the text of each page fragment of a table, never
    shared, because the layout of the pages may differ (e.g. centered tables).
    """

    def __init__(self, diagnostics: DiagnosticsReporter | None = None) -> None:
        self._diagnostics = (
            diagnostics if diagnostics is not None else DiagnosticsReporter()
        )

    def parse(
        self, fragment_text: str, declaration: TableDeclaration
    ) -> list[list[str]]:
        """The rows (lists of cell texts) of a fragment of a table."""
        lines = [line.rstrip() for line in fragment_text.split("\n")]
        non_blank_lines = [line for line in lines if line.strip()]
        if not non_blank_lines:
            return []
        # A line spanning all the columns would close the gutters
        column_lines = [
            line
            for line in non_blank_lines
            if not self._is_spanning_row(line, declaration)
        ]
        column_starts = self._find_column_starts(
            column_lines or non_blank_lines, declaration.minimum_gutter_width
        )
        if column_lines and len(column_starts) != declaration.column_count:
            self._diagnostics.warn(
                f"Table {declaration.name!r}: expected {declaration.column_count} "
                f"columns but found {len(column_starts)} in:\n{fragment_text}"
            )
        if declaration.row_strategy == TableDeclaration.ROW_PER_LINE:
            return [self._cut_line(line, column_starts) for line in non_blank_lines]
        if declaration.row_strategy == TableDeclaration.ROW_PER_BLANK_LINE:
            return self._read_rows_separated_by_blank_lines(lines, column_starts)
        if declaration.row_strategy == TableDeclaration.ROW_PER_PATTERN:
            return self._read_rows_starting_with_pattern(
                non_blank_lines, column_starts, declaration
            )
        raise ValueError(f"Unknown table row strategy {declaration.row_strategy!r}.")

    @staticmethod
    def _is_spanning_row(line: str, declaration: TableDeclaration) -> bool:
        return (
            declaration.spanning_row_pattern is not None
            and declaration.spanning_row_pattern.search(line.strip()) is not None
        )

    def _read_rows_starting_with_pattern(
        self,
        non_blank_lines: list[str],
        column_starts: list[int],
        declaration: TableDeclaration,
    ) -> list[list[str]]:
        """The rows of a table whose rows start at the lines matching a pattern.

        The lines that do not start a row complete the cells of the current
        row. When the first column holds labels spanning many rows, the text of
        the first column is kept apart: it is given, as a label, to the first
        row following the previous spanning row (see TableDeclaration).
        """
        column_count = len(column_starts)
        rows: list[list[str]] = []
        current_row: list[list[str]] | None = None  # the cell pieces of each column
        # Where the rows of the current group (those between two spanning rows)
        # start in rows, and the label pieces found beside them
        group_first_row_index: int | None = None
        label_pieces: list[str] = []

        def finish_current_row() -> None:
            nonlocal current_row
            if current_row is not None:
                rows.append([self.join_wrapped_text(pieces) for pieces in current_row])
                current_row = None

        def finish_group() -> None:
            nonlocal group_first_row_index, label_pieces
            finish_current_row()
            if label_pieces and group_first_row_index is not None:
                rows[group_first_row_index][0] = self.join_wrapped_text(label_pieces)
            group_first_row_index = None
            label_pieces = []

        for line in non_blank_lines:
            if self._is_spanning_row(line, declaration):
                finish_group()
                rows.append(
                    [SpanningCellText(line.strip())] + [""] * (column_count - 1)
                )
                continue
            cells = self._cut_line(line, column_starts)
            if declaration.first_column_spans_rows:
                label_pieces.append(cells[0])
                cells[0] = ""
            starts_row = declaration.row_start_pattern is not None and bool(
                declaration.row_start_pattern.search(cells[-1])
            )
            if starts_row:
                finish_current_row()
                if group_first_row_index is None:
                    group_first_row_index = len(rows)
                current_row = [[] for _ in range(column_count)]
            if current_row is None:
                # Text before the first row start (e.g. the label of a group
                # whose rows started on the previous page)
                continue
            for column, cell in enumerate(cells):
                current_row[column].append(cell)
        finish_group()
        return rows

    @staticmethod
    def _find_column_starts(lines: list[str], minimum_gutter_width: int) -> list[int]:
        width = max(len(line) for line in lines)
        occupied = [False] * width
        for line in lines:
            for position, character in enumerate(line):
                if character != " ":
                    occupied[position] = True
        column_starts = []
        # Starting with a gutter lets the first occupied position start a column
        blank_width = minimum_gutter_width
        for position, is_occupied in enumerate(occupied):
            if not is_occupied:
                blank_width += 1
                continue
            if blank_width >= minimum_gutter_width:
                column_starts.append(position)
            blank_width = 0
        return column_starts

    @staticmethod
    def _cut_line(line: str, column_starts: list[int]) -> list[str]:
        column_ends = column_starts[1:] + [None]
        return [
            line[start:end].strip() for start, end in zip(column_starts, column_ends)
        ]

    def _read_rows_separated_by_blank_lines(
        self, lines: list[str], column_starts: list[int]
    ) -> list[list[str]]:
        rows = []
        block_lines: list[str] = []
        for line in lines + [""]:
            if line.strip():
                block_lines.append(line)
                continue
            if block_lines:
                rows.append(self._merge_wrapped_lines(block_lines, column_starts))
                block_lines = []
        return rows

    def _merge_wrapped_lines(
        self, block_lines: list[str], column_starts: list[int]
    ) -> list[str]:
        """The cells of a row whose cells are wrapped on many lines."""
        cut_lines = [self._cut_line(line, column_starts) for line in block_lines]
        return [
            self.join_wrapped_text([cut_line[column] for cut_line in cut_lines])
            for column in range(len(column_starts))
        ]

    @staticmethod
    def join_wrapped_text(text_pieces: list[str]) -> str:
        """Glue the pieces of a text wrapped on many lines.

        A piece ending with a hyphen is glued to the next one without
        whitespace (e.g. "fame-" and "obscurity"), the other ones are
        separated by a single whitespace. Empty pieces are ignored.
        """
        joined_text = ""
        for piece in text_pieces:
            piece = piece.strip()
            if not piece:
                continue
            if not joined_text:
                joined_text = piece
            elif joined_text.endswith("-"):
                joined_text += piece
            else:
                joined_text += " " + piece
        return joined_text

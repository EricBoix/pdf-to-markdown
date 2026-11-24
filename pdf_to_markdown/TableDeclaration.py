import re


class TableDeclaration:
    """What the structural information of a book tells about one of its tables.

    A table cannot be detected automatically with enough reliability: the
    structural information of the book thus declares each of its tables. A
    declaration tells where the table starts and ends in the layout text of the
    pages, and how the rows of the table are to be read.

    The table is looked for in the layout text of the pages, that is the text
    in which the columns of a table are separated by runs of whitespaces.
    """

    # A row is a single line of the layout text.
    ROW_PER_LINE = "line"
    # A row is a block of consecutive lines, the blocks being separated by
    # blank lines. The lines of a block are the wrapped lines of the cells of
    # the row.
    ROW_PER_BLANK_LINE = "blank_line"
    # A row starts at each line whose last cell matches the row start pattern,
    # the other lines being the wrapped lines of the cells of the row. The
    # blank lines are ignored.
    ROW_PER_PATTERN = "pattern"

    def __init__(
        self,
        name: str,
        start_pattern: str,
        column_count: int,
        end_pattern: str | None = None,
        row_strategy: str = ROW_PER_LINE,
        has_column_headings: bool = True,
        start_page_number: int | None = None,
        minimum_gutter_width: int = 3,
        row_start_pattern: str | None = None,
        spanning_row_pattern: str | None = None,
        first_column_spans_rows: bool = False,
    ) -> None:
        """
        :param name: identifies the table (unique within a document).
        :param start_pattern: regular expression matching the beginning of the
            table. It must be anchored at the beginning of a line (^). The
            match ends where the rows start, unless the pattern is a lookahead
            in which case the rows start at the match. When the pattern holds a
            group named "caption" its text is the caption of the table.
        :param column_count: expected number of columns, a different count
            found in the layout text is reported.
        :param end_pattern: regular expression anchored at the beginning of the
            first line that follows the table. The table may spread over many
            pages: it stops at the first page where the pattern is found. When
            None the table ends with the page on which it starts.
        :param row_strategy: ROW_PER_LINE, ROW_PER_BLANK_LINE or
            ROW_PER_PATTERN.
        :param has_column_headings: whether the first row of the table is made
            of the headings of its columns. When it is not, the caption (if
            any) is what stands in the header row that markdown requires.
        :param start_page_number: restricts the search of the start pattern to
            that page of the document (the pdf page index).
        :param minimum_gutter_width: the width of the blank vertical strip (made
            of whitespaces in every line of the table) that separates two
            columns.
        :param row_start_pattern: ROW_PER_PATTERN only: regular expression
            matching the text of the last cell of the line that starts a row.
        :param spanning_row_pattern: regular expression matching a line that
            spans all the columns (e.g. a milestone between two groups of rows).
            Such a line is a row of its own, left out of the detection of the
            columns. Markdown having no colspan, the text of such a row goes
            in its first cell, the other cells being filled with a separator.
        :param first_column_spans_rows: ROW_PER_PATTERN only: the first column
            holds labels that span many rows, vertically centered next to
            them. The labels found between two spanning rows (or the ends of a
            page) are those of the rows between them: a label is written in the
            first row it spans, the cells below are left empty.
        """
        self.name = name
        self.start_pattern = re.compile(start_pattern, re.MULTILINE)
        self.column_count = column_count
        self.end_pattern = (
            re.compile(end_pattern, re.MULTILINE) if end_pattern is not None else None
        )
        self.row_strategy = row_strategy
        self.has_column_headings = has_column_headings
        self.start_page_number = start_page_number
        self.minimum_gutter_width = minimum_gutter_width
        self.row_start_pattern = (
            re.compile(row_start_pattern) if row_start_pattern is not None else None
        )
        self.spanning_row_pattern = (
            re.compile(spanning_row_pattern)
            if spanning_row_pattern is not None
            else None
        )
        self.first_column_spans_rows = first_column_spans_rows

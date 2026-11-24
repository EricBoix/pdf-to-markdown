class SpanningCellText(str):
    """The first cell of a row that spans all the columns of a table.

    Markdown having no colspan, such a row holds its text in its first cell
    (see Table) and its other cells are left to be filled with a separator.
    """


class TableContent:
    """The cells of a table, as read from the layout text of the pdf pages."""

    def __init__(
        self,
        name: str,
        caption: str | None,
        has_column_headings: bool,
    ) -> None:
        self.name = name
        self.caption = caption
        self.has_column_headings = has_column_headings
        # A row is a list of cell texts. When the table has column headings
        # the first row is the one of the headings.
        self.rows: list[list[str]] = []


class TableRegistry:
    """Keeps the tables cut out of the pages until the document is built.

    See TablePlaceholder for what stands in the text of the pages.
    """

    def __init__(self) -> None:
        self._contents: dict[str, TableContent] = {}

    def add(self, content: TableContent) -> None:
        self._contents[content.name] = content

    def get(self, table_name: str) -> TableContent | None:
        return self._contents.get(table_name)

    def has(self, table_name: str) -> bool:
        return table_name in self._contents

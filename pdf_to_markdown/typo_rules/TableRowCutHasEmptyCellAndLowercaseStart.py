from .TypoRule import TypoRule


class TableRowCutHasEmptyCellAndLowercaseStart(TypoRule):
    """A row of a table was cut by a page break when two signals come together: a
    cell is empty in the last row of the page while it holds text in the first
    row of the next page, and a cell of that first row starts with a lowercase
    letter (the text goes on).

    Action site: TableExtractor._decide_row_continuation. The declaration of the
    page (table_row_continues) wins over the rule. Trap: the decision and its
    reason are reported with the page (TableExtractor).
    """

    def row_continues(
        self, last_row: list[str], first_new_row: list[str]
    ) -> tuple[bool, str]:
        """Whether the first row of a page continues the last row of the page
        before, and why."""
        complementary_cell = any(
            not previous_cell and new_cell
            for previous_cell, new_cell in zip(last_row, first_new_row)
        )
        lowercase_start = any(cell[:1].islower() for cell in first_new_row)
        if complementary_cell and lowercase_start:
            return True, "empty cell completed and lowercase start"
        return False, "no complementary empty cell or no lowercase start"

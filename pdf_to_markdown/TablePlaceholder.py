import re


class TablePlaceholder:
    """The single line standing for a table within the text of a page.

    A table is cut out of the text of its page before the text is broken into
    chapters and paragraphs (the capital letters of its cells would be taken
    for chapter names, its lines for paragraphs...). The line left in place of
    the table lets the splitters tell where the table was, the table itself
    being kept by the TableRegistry under the name found in the placeholder.
    """

    PATTERN = re.compile(r"^<<table:(?P<table_name>[^>\n]+)>>$", re.MULTILINE)

    @staticmethod
    def make(table_name: str) -> str:
        return f"<<table:{table_name}>>"

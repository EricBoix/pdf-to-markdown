from .TypoRule import TypoRule


class TableRowIsOnItsPrintedPage(TypoRule):
    """Each row of a table belongs to the page where the PDF prints it.

    Implicit rule: a design choice of pdf-to-markdown, always true. The code does
    not meet it yet: a Table carries a single page, hence the rows of a table cut
    by a page break are attributed to the page where the table starts.
    """

    configurable = False

from .TypoRule import TypoRule


class ReadingOrderIsLineOrder(TypoRule):
    """The reading order of a page is the extractor's line order (top to bottom,
    one text flow).

    The converter relies on it everywhere it reads the text of a page. Trap: the
    page break validator checks the order of the pages only; the order inside a
    page cannot be checked (see docs/rules_configurable.md).
    """

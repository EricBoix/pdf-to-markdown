from .TypoRule import TypoRule


class HeadingIsOnItsPrintedPage(TypoRule):
    """A heading belongs to the page where the PDF prints it, never to the page
    of its body.

    Implicit rule: a design choice of pdf-to-markdown, always true. A reader who
    cites a heading must land on its exact page.
    """

    configurable = False

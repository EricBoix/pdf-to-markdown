from ..Model import DocumentHierarchicalLevel
from ..PageLayout import PageLayout
from .TypoRule import TypoRule


class HeadingIsOnItsPrintedPage(TypoRule):
    """A heading belongs to the page where the PDF prints it, never to the page
    of its body.

    Implicit rule: a design choice of pdf-to-markdown, always true. A reader who
    cites a heading must land on its exact page.

    It acts in LevelBreaker.break_into_sublevels, where the name of a level may be
    printed on a page and the text it names start on the next one.
    """

    configurable = False

    def page_of_level(
        self, name_layout: PageLayout | None, text_layout: PageLayout
    ) -> PageLayout:
        """The page that a level is on: the one its name is printed on
        (name_layout, None when the name stands on the page of its text, see
        text_layout)."""
        if name_layout is None:
            return text_layout
        return name_layout.__copy__()

    def contradicted_by(
        self, level: DocumentHierarchicalLevel, name_layout: PageLayout | None
    ) -> bool:
        """Whether the level is not on the page where its name is printed.

        A trap, not a decision. It only runs where the rule acts: it cannot see
        a heading that other code put on a wrong page."""
        if name_layout is None:
            return False
        return level.page_layout.page_number != name_layout.page_number

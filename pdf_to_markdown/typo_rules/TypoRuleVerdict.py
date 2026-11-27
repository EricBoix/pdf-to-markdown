from enum import Enum


class TypoRuleVerdict(Enum):
    """What a rule says about two pieces of text on both sides of a page break."""

    # The tail continues the head: they belong to the same paragraph.
    CONTINUES = "continues"
    # The tail starts a new paragraph.
    NEW_PARAGRAPH = "new_paragraph"
    # The rule does not apply to this page break.
    NO_OPINION = "no_opinion"

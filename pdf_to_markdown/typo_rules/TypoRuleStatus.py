from enum import Enum


class TypoRuleStatus(Enum):
    """What a document declares about a typographic rule (see TypoRule).

    The code only acts on, and only checks, a rule that HOLDS. A rule that is
    not mentioned by the document is UNKNOWN: declaring nothing never changes
    what the converter does.
    """

    HOLDS = "holds"
    DOES_NOT_HOLD = "does_not_hold"
    UNKNOWN = "unknown"

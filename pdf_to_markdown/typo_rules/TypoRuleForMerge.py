import re
from abc import abstractmethod
from typing import ClassVar

from ..Model import Sentence
from .TypoRule import TypoRule
from .TypoRuleVerdict import TypoRuleVerdict


class TypoRuleForMerge(TypoRule):
    """A rule deciding whether the text starting a page continues the paragraph
    that ends the previous page.

    It looks at the last sentence of the head (what ends the previous page) and
    at the first sentence of the tail (what starts the page). The rules are asked
    in a fixed order by ParagraphMerger, the first verdict that is not NO_OPINION
    decides.
    """

    # A sentence is complete when it ends with a terminal punctuation mark,
    # possibly followed by closing quotes or brackets and by a footnote number
    # (as in "...in the same system.11"). The trailing footnote number is fixed
    # here: it is not a configurable rule (see docs/rules_possible.md,
    # DigitsAfterPunctuationAreFootnotes).
    TERMINAL_PUNCTUATION: ClassVar[re.Pattern] = re.compile(r"[.!?…][\"'”’)\]]*\d*$")

    @classmethod
    def ends_with_terminal_punctuation(cls, sentence: Sentence) -> bool:
        return bool(cls.TERMINAL_PUNCTUATION.search(sentence.text))

    @abstractmethod
    def verdict(self, head: Sentence, tail: Sentence) -> TypoRuleVerdict:
        """What this rule says about the page break between head and tail."""
        ...

    def contradicted_by(self, head: Sentence, tail: Sentence) -> bool:
        """Whether this page break contradicts the rule, supposing it holds.

        A trap, not a decision: a document that declares the rule is warned
        about the page breaks that look wrong to it (it may have declared the
        rule by mistake). The default finds nothing to contradict.
        """
        return False

    def supported_by(self, head: Sentence, tail: Sentence) -> bool:
        """Whether this page break is an instance of the rule (the rule decides
        it and nothing contradicts it)."""
        return self.verdict(
            head, tail
        ) is not TypoRuleVerdict.NO_OPINION and not self.contradicted_by(head, tail)

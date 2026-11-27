from ..Model import Sentence
from .TypoRuleForMerge import TypoRuleForMerge
from .TypoRuleVerdict import TypoRuleVerdict


class LowercaseTailContinues(TypoRuleForMerge):
    """A lowercase start on the next page continues the paragraph of the page before.

    Trap: a lowercase start after a head that ends with a terminal punctuation
    (an uncommon start for a sentence that follows a complete one).
    """

    def verdict(self, head: Sentence, tail: Sentence) -> TypoRuleVerdict:
        if tail.text[:1].islower():
            return TypoRuleVerdict.CONTINUES
        return TypoRuleVerdict.NO_OPINION

    def contradicted_by(self, head: Sentence, tail: Sentence) -> bool:
        return self.verdict(
            head, tail
        ) is TypoRuleVerdict.CONTINUES and self.ends_with_terminal_punctuation(head)

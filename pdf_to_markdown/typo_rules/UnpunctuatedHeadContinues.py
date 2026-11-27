from ..Model import Sentence
from .TypoRuleForMerge import TypoRuleForMerge
from .TypoRuleVerdict import TypoRuleVerdict


class UnpunctuatedHeadContinues(TypoRuleForMerge):
    """A last sentence without terminal punctuation continues on the next page.

    Trap: an uppercase start after such a head (the continuation of a sentence
    usually starts in lowercase).
    """

    def verdict(self, head: Sentence, tail: Sentence) -> TypoRuleVerdict:
        if not self.ends_with_terminal_punctuation(head):
            return TypoRuleVerdict.CONTINUES
        return TypoRuleVerdict.NO_OPINION

    def contradicted_by(self, head: Sentence, tail: Sentence) -> bool:
        return (
            self.verdict(head, tail) is TypoRuleVerdict.CONTINUES
            and tail.text[:1].isupper()
        )

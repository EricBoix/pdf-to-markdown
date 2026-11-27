from ..Model import Sentence
from .TypoRuleForMerge import TypoRuleForMerge
from .TypoRuleVerdict import TypoRuleVerdict


class CompleteHeadUppercaseTailStartsParagraph(TypoRuleForMerge):
    """A complete last sentence followed by an uppercase start on the next page
    begins a new paragraph.

    No trap yet: nothing in the text of the two sentences tells that such a
    page break is a continuation (a first-line indent might, see
    docs/rules_possible.md, IndentedTailStartsParagraph).
    """

    def verdict(self, head: Sentence, tail: Sentence) -> TypoRuleVerdict:
        if self.ends_with_terminal_punctuation(head) and tail.text[:1].isupper():
            return TypoRuleVerdict.NEW_PARAGRAPH
        return TypoRuleVerdict.NO_OPINION

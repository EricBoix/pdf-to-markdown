import re

from .TypoRule import TypoRule


class SpacedEllipsisIsAnEllipsis(TypoRule):
    """Dots separated by spaces (". . .") are one ellipsis, spelled "...".

    The sentence tokenizer does not see a spaced ellipsis as such: it cuts it
    into one sentence per dot e.g. 'there is .', '.', '.' whereas a plain
    ellipsis stays within its sentence. The rule must thus be applied before the
    text gets tokenized into sentences.

    Action site: TextExtractor.extract_all. Trap: the number of substitutions
    of a page is reported (a page where a book that holds the rule has dots
    separated by spaces for another purpose would show it).
    """

    SPACED_ELLIPSIS = re.compile(r"(?<=\S) ?\. \. \.")

    def normalize(self, text: str) -> str:
        return self.SPACED_ELLIPSIS.sub("...", text)

    def substitution_count(self, text: str) -> int:
        """How many spaced ellipses the text holds."""
        return len(self.SPACED_ELLIPSIS.findall(text))

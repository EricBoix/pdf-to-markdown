from abc import abstractmethod

from .TypoRule import TypoRule


class TypoRuleForCharacters(TypoRule):
    """A rule folding some characters of the text of a page to ASCII.

    The rules are applied by TextSanitizer.sanitize_characters, after the
    folding of the typographic quotes and dashes (a fact, see
    docs/rules_implicit.md).
    """

    @abstractmethod
    def fold(self, text: str) -> str:
        """The text, the characters of the rule folded."""
        ...

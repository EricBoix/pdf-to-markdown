from typing import Iterable, Mapping

from ..Errors import ConverterError
from .CompleteHeadUppercaseTailStartsParagraph import (
    CompleteHeadUppercaseTailStartsParagraph,
)
from .BlockquoteRepeatingParagraphIsDropped import BlockquoteRepeatingParagraphIsDropped
from .DiacriticsFoldToBaseLetters import DiacriticsFoldToBaseLetters
from .HeadingIsOnItsPrintedPage import HeadingIsOnItsPrintedPage
from .LayoutTextCarriesIndentationAndColumns import (
    LayoutTextCarriesIndentationAndColumns,
)
from .LowercaseTailContinues import LowercaseTailContinues
from .NumberedItemStartingAPageIsNotAContinuation import (
    NumberedItemStartingAPageIsNotAContinuation,
)
from .ReadingOrderIsLineOrder import ReadingOrderIsLineOrder
from .SmileyGlyphsFoldToAnEmoticon import SmileyGlyphsFoldToAnEmoticon
from .SpacedEllipsisIsAnEllipsis import SpacedEllipsisIsAnEllipsis
from .TableRowCutHasEmptyCellAndLowercaseStart import (
    TableRowCutHasEmptyCellAndLowercaseStart,
)
from .TableRowIsOnItsPrintedPage import TableRowIsOnItsPrintedPage
from .TypoRule import TypoRule
from .TypoRuleForCharacters import TypoRuleForCharacters
from .TypoRuleForMerge import TypoRuleForMerge
from .UnpunctuatedHeadContinues import UnpunctuatedHeadContinues


class TypoRuleRegister:
    """The typographic rules the converter knows, by name."""

    def __init__(self, rules: Iterable[TypoRule]) -> None:
        self._rules: dict[str, TypoRule] = {}
        for rule in rules:
            if rule.name in self._rules:
                raise ConverterError(
                    f"The typographic rule {rule.name} is registered twice."
                )
            self._rules[rule.name] = rule

    @classmethod
    def default(
        cls, diacritic_foldings: Mapping[str, str] | None = None
    ) -> "TypoRuleRegister":
        """All the rules of the package. The order in which the rules for the merge
        of a paragraph cut by a page break are listed is the order in which
        ParagraphMerger asks them: the first verdict that is not NO_OPINION decides.

        The diacritics that DiacriticsFoldToBaseLetters folds are those a document
        declares (None: the default ones)."""
        return cls(
            [
                LowercaseTailContinues(),
                UnpunctuatedHeadContinues(),
                CompleteHeadUppercaseTailStartsParagraph(),
                ReadingOrderIsLineOrder(),
                SpacedEllipsisIsAnEllipsis(),
                DiacriticsFoldToBaseLetters(diacritic_foldings),
                SmileyGlyphsFoldToAnEmoticon(),
                LayoutTextCarriesIndentationAndColumns(),
                BlockquoteRepeatingParagraphIsDropped(),
                NumberedItemStartingAPageIsNotAContinuation(),
                TableRowCutHasEmptyCellAndLowercaseStart(),
                HeadingIsOnItsPrintedPage(),
                TableRowIsOnItsPrintedPage(),
            ]
        )

    def knows(self, name: str) -> bool:
        return name in self._rules

    def get(self, name: str) -> TypoRule:
        if name not in self._rules:
            raise ConverterError(
                f"Unknown typographic rule {name!r}. Known rules: "
                f"{', '.join(sorted(self._rules))}."
            )
        return self._rules[name]

    def all(self) -> list[TypoRule]:
        return list(self._rules.values())

    def character_rules(self) -> list[TypoRuleForCharacters]:
        return [
            rule
            for rule in self._rules.values()
            if isinstance(rule, TypoRuleForCharacters)
        ]

    def merge_rules(self) -> list[TypoRuleForMerge]:
        return [
            rule for rule in self._rules.values() if isinstance(rule, TypoRuleForMerge)
        ]

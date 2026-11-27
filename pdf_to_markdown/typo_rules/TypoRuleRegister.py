from typing import Iterable

from ..Errors import ConverterError
from .CompleteHeadUppercaseTailStartsParagraph import (
    CompleteHeadUppercaseTailStartsParagraph,
)
from .HeadingIsOnItsPrintedPage import HeadingIsOnItsPrintedPage
from .LowercaseTailContinues import LowercaseTailContinues
from .ReadingOrderIsLineOrder import ReadingOrderIsLineOrder
from .TableRowIsOnItsPrintedPage import TableRowIsOnItsPrintedPage
from .TypoRule import TypoRule
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
    def default(cls) -> "TypoRuleRegister":
        """All the rules of the package. The order in which the rules for the merge
        of a paragraph cut by a page break are listed is the order in which
        ParagraphMerger asks them: the first verdict that is not NO_OPINION decides."""
        return cls(
            [
                LowercaseTailContinues(),
                UnpunctuatedHeadContinues(),
                CompleteHeadUppercaseTailStartsParagraph(),
                ReadingOrderIsLineOrder(),
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

    def merge_rules(self) -> list[TypoRuleForMerge]:
        return [
            rule for rule in self._rules.values() if isinstance(rule, TypoRuleForMerge)
        ]

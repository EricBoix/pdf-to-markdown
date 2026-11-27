from abc import ABC
from typing import ClassVar


class TypoRule(ABC):
    """A typographic rule: a convention of a book that the converter may rely on.

    A rule is identified by its name, which is the name of its class (a slug, there
    is no number and no order among the rules). A rule is either:
    - configurable: a typographic convention local to a book. A document declares
      it holds (StructuralInfoBase.valid_rules) or does not hold
      (StructuralInfoBase.rejected_rules); it is unknown to a document that
      declares neither. See docs/rules_configurable.md.
    - implicit (configurable = False): a design choice of pdf-to-markdown, always
      true, that a document never declares. See docs/rules_implicit.md.

    The rules that are candidates only (no code relies on them yet) are not
    classes: see docs/rules_possible.md.
    """

    configurable: ClassVar[bool] = True
    # The slug of the rule: always the name of the class (see __init_subclass__)
    name: ClassVar[str]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.name = cls.__name__

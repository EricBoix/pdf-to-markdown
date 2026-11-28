"""The typographic rules are used by the code, not only described by it.

Every rule has an action site in the package, outside typo_rules/, that receives
it from the structural information (StructuralInfoBase.rule_register).
"""

import ast
from pathlib import Path

import pytest

import pdf_to_markdown
from pdf_to_markdown import StructuralInfoBase, TypoRuleRegister
from pdf_to_markdown.typo_rules import TypoRule

PACKAGE_DIRECTORY = Path(pdf_to_markdown.__file__).parent

# The rules that no code can act on yet, each flagged as unmet in its entry of
# docs/rules_implicit.md.
RULES_WITHOUT_ACTION_SITE = {"TableRowIsOnItsPrintedPage"}

# The modules where the rules are not an action site: they define them or
# export them.
MODULES_THAT_ARE_NOT_ACTION_SITES = {"__init__.py"}


def _package_modules() -> list[Path]:
    """The modules of the package (a local virtual environment that may stand
    inside the package directory is not part of it)."""
    return [
        path
        for path in sorted(PACKAGE_DIRECTORY.rglob("*.py"))
        if not {"venv", ".venv", "__pycache__"}
        & set(path.relative_to(PACKAGE_DIRECTORY).parts)
    ]


def _action_site_modules() -> list[Path]:
    typo_rules_directory = PACKAGE_DIRECTORY / "typo_rules"
    return [
        path
        for path in _package_modules()
        if typo_rules_directory not in path.parents
        and path.name not in MODULES_THAT_ARE_NOT_ACTION_SITES
    ]


def _names_used_in(path: Path) -> set[str]:
    """The names and the attributes that a module uses, its imports included."""
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)
    return names


def _rule_names_of(rule: TypoRule) -> set[str]:
    """The name of the rule and of its base classes (the code may act on a
    family of rules, e.g. TypoRuleForMerge), the base TypoRule left aside."""
    return {
        base.__name__
        for base in type(rule).__mro__
        if issubclass(base, TypoRule) and base is not TypoRule
    }


class TestEveryRuleHasAnActionSite:
    @pytest.mark.parametrize(
        "rule", TypoRuleRegister.default().all(), ids=lambda rule: rule.name
    )
    def test_a_rule_is_used_by_the_code(self, rule):
        used_names = set()
        for path in _action_site_modules():
            used_names |= _names_used_in(path)
        is_used = bool(_rule_names_of(rule) & used_names)
        if rule.name in RULES_WITHOUT_ACTION_SITE:
            assert not is_used, (
                f"{rule.name} has an action site: remove it from "
                "RULES_WITHOUT_ACTION_SITE"
            )
        else:
            assert is_used, (
                f"No code outside typo_rules/ acts on the rule {rule.name}: "
                "give it an action site (see docs/rules_implicit.md)"
            )

    def test_the_rules_without_action_site_are_flagged_unmet_in_the_docs(self):
        documentation = (
            PACKAGE_DIRECTORY.parent / "docs" / "rules_implicit.md"
        ).read_text(encoding="utf-8")
        for rule_name in RULES_WITHOUT_ACTION_SITE:
            assert f"## {rule_name}" in documentation
            assert "no code acts on it yet" in documentation.split(f"## {rule_name}")[1]


class TestTheRulesFlowFromTheStructuralInformation:
    def test_only_the_structural_information_builds_the_register(self):
        builders = []
        for path in _package_modules():
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr == "default"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "TypoRuleRegister"
                ):
                    builders.append(path.name)
        assert sorted(set(builders)) == ["StructuralInfoBase.py"]

    def test_the_rule_register_is_the_one_of_the_structural_information(self):
        class _StructuralInfo(StructuralInfoBase):
            pages_info = {}
            total_page_number = 1
            valid_rules = frozenset({"LowercaseTailContinues"})

        structural_info = _StructuralInfo()
        assert structural_info.rule_if_holds("LowercaseTailContinues") is (
            structural_info.rule_register.get("LowercaseTailContinues")
        )
        assert structural_info.rule_if_holds("UnpunctuatedHeadContinues") is None

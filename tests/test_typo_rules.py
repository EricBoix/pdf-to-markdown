"""The register of typographic rules and their declaration by a document."""

from pathlib import Path

import pytest

from pdf_to_markdown import (
    ConverterError,
    StructuralInfoBase,
    TypoRuleRegister,
    TypoRuleStatus,
)
from pdf_to_markdown.typo_rules import (
    HeadingIsOnItsPrintedPage,
    LowercaseTailContinues,
    UnpunctuatedHeadContinues,
)


def _structural_info(valid_rules=frozenset(), rejected_rules=frozenset()):
    class _StructuralInfo(StructuralInfoBase):
        pages_info = {}
        total_page_number = 1

    _StructuralInfo.valid_rules = frozenset(valid_rules)
    _StructuralInfo.rejected_rules = frozenset(rejected_rules)
    return _StructuralInfo()


class TestTypoRuleName:
    def test_the_name_of_a_rule_is_the_name_of_its_class(self):
        assert LowercaseTailContinues.name == "LowercaseTailContinues"
        assert LowercaseTailContinues().name == "LowercaseTailContinues"


class TestTypoRuleRegister:
    def test_get_by_name(self):
        register = TypoRuleRegister.default()
        assert isinstance(
            register.get("LowercaseTailContinues"), LowercaseTailContinues
        )

    def test_get_unknown_name_raises(self):
        with pytest.raises(ConverterError, match="Unknown typographic rule"):
            TypoRuleRegister.default().get("LowercaseTailContinue")

    def test_registering_a_rule_twice_raises(self):
        with pytest.raises(ConverterError, match="registered twice"):
            TypoRuleRegister([LowercaseTailContinues(), LowercaseTailContinues()])

    def test_merge_rules_are_in_the_order_they_are_asked(self):
        names = [rule.name for rule in TypoRuleRegister.default().merge_rules()]
        assert names == [
            "LowercaseTailContinues",
            "UnpunctuatedHeadContinues",
            "CompleteHeadUppercaseTailStartsParagraph",
        ]

    def test_every_rule_has_an_entry_in_the_documentation(self):
        documentation = "".join(
            path.read_text()
            for path in (Path(__file__).parent.parent / "docs").glob("rules_*.md")
        )
        for rule in TypoRuleRegister.default().all():
            assert rule.name in documentation, rule.name


class TestRuleStatus:
    def test_a_rule_that_is_not_declared_is_unknown(self):
        structural_info = _structural_info()
        assert (
            structural_info.rule_status("LowercaseTailContinues")
            is TypoRuleStatus.UNKNOWN
        )
        assert not structural_info.rule_holds("LowercaseTailContinues")

    def test_a_valid_rule_holds(self):
        structural_info = _structural_info(valid_rules={"LowercaseTailContinues"})
        assert structural_info.rule_holds("LowercaseTailContinues")
        assert (
            structural_info.rule_status("UnpunctuatedHeadContinues")
            is TypoRuleStatus.UNKNOWN
        )

    def test_a_rejected_rule_does_not_hold(self):
        structural_info = _structural_info(rejected_rules={"LowercaseTailContinues"})
        assert (
            structural_info.rule_status("LowercaseTailContinues")
            is TypoRuleStatus.DOES_NOT_HOLD
        )
        assert not structural_info.rule_holds("LowercaseTailContinues")

    def test_an_implicit_rule_always_holds(self):
        assert _structural_info().rule_holds(HeadingIsOnItsPrintedPage.name)

    def test_the_status_of_an_unknown_rule_name_raises(self):
        with pytest.raises(ConverterError, match="Unknown typographic rule"):
            _structural_info().rule_status("NoSuchRule")

    def test_declaring_an_unknown_rule_raises(self):
        with pytest.raises(ConverterError, match="Unknown typographic rule"):
            _structural_info(valid_rules={"NoSuchRule"})

    def test_declaring_a_rule_both_valid_and_rejected_raises(self):
        with pytest.raises(ConverterError, match="both valid and rejected"):
            _structural_info(
                valid_rules={UnpunctuatedHeadContinues.name},
                rejected_rules={UnpunctuatedHeadContinues.name},
            )

    def test_declaring_an_implicit_rule_raises(self):
        with pytest.raises(ConverterError, match="implicit"):
            _structural_info(valid_rules={HeadingIsOnItsPrintedPage.name})

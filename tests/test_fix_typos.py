"""TypoFixer corrects the upstream typos that a StructuralInfo declares per page."""

import logging

from pdf_to_markdown import ExtractedPage, PageLayout, TypoFixer

from .fixtures.fixture_structural_info import FixtureStructuralInfo

LOGGER_NAME = "pdf_to_markdown"


class _TypoStructuralInfo(FixtureStructuralInfo):
    def __init__(self, typo_and_fix) -> None:
        super().__init__()
        self._typo_and_fix = typo_and_fix

    @property
    def pages_info(self) -> dict:
        return {1: {"typo_and_fix": self._typo_and_fix}}


def _fix_typos(structural_info, extracted_page) -> None:
    """What the DocumentBreaker does with the typos declared for the page."""
    typo_fixes = structural_info.page_info(extracted_page.page_number).typo_fixes
    TypoFixer().fix(extracted_page, typo_fixes)


def _extracted_page(page_number, text) -> ExtractedPage:
    extracted_page = ExtractedPage(
        page_number, PageLayout(page_number, page_number), None
    )
    extracted_page.set_text(text)
    return extracted_page


def test_single_fix_is_applied_on_every_occurrence():
    structural_info = _TypoStructuralInfo({"typo": "teh", "fix": "the"})
    extracted_page = _extracted_page(1, "teh mind and teh body")
    _fix_typos(structural_info, extracted_page)
    assert extracted_page.text == "the mind and the body"


def test_list_of_fixes_is_applied_in_order():
    structural_info = _TypoStructuralInfo(
        [{"typo": "teh", "fix": "the"}, {"typo": "mnd", "fix": "mind"}]
    )
    extracted_page = _extracted_page(1, "teh mnd")
    _fix_typos(structural_info, extracted_page)
    assert extracted_page.text == "the mind"


def test_typo_is_a_regular_expression():
    structural_info = _TypoStructuralInfo({"typo": r"(\w+)  (\w+)", "fix": r"\1 \2"})
    extracted_page = _extracted_page(1, "calm  mind")
    _fix_typos(structural_info, extracted_page)
    assert extracted_page.text == "calm mind"


def test_page_without_declared_typo_is_left_untouched():
    structural_info = _TypoStructuralInfo({"typo": "teh", "fix": "the"})
    extracted_page = _extracted_page(2, "teh mind")
    _fix_typos(structural_info, extracted_page)
    assert extracted_page.text == "teh mind"


def test_typo_not_found_warns_and_leaves_the_text_untouched(caplog):
    structural_info = _TypoStructuralInfo({"typo": "teh", "fix": "the"})
    extracted_page = _extracted_page(1, "the mind")
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        _fix_typos(structural_info, extracted_page)
    assert extracted_page.text == "the mind"
    assert any(
        "Couldn't find typo in extracted page number 1" in record.getMessage()
        for record in caplog.records
    )


def test_a_fix_not_found_does_not_prevent_the_next_ones():
    structural_info = _TypoStructuralInfo(
        [{"typo": "absent", "fix": "x"}, {"typo": "teh", "fix": "the"}]
    )
    extracted_page = _extracted_page(1, "teh mind")
    _fix_typos(structural_info, extracted_page)
    assert extracted_page.text == "the mind"

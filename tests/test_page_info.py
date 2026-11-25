"""PageInfo is the checked view of what a StructuralInfoBase declares per page."""

import pytest

from pdf_to_markdown import (
    ConverterError,
    PageInfo,
    StructuralInfoBase,
    TypoFix,
)


class TestPageInfoFromDeclaration:
    def test_empty_declaration_gets_the_defaults(self):
        assert PageInfo.from_declaration(1, {}) == PageInfo()
        page_info = PageInfo()
        assert page_info.kind is None
        assert page_info.chapter_name is None
        assert not page_info.is_chapter
        assert not page_info.drop_page
        assert page_info.typo_fixes == ()
        assert page_info.table_row_continues is None
        assert not page_info.no_new_chapter
        assert not page_info.paragraph_fits_on_page
        assert not page_info.blockquote_fits_on_page

    def test_flags(self):
        page_info = PageInfo.from_declaration(
            1,
            {
                "drop_page": True,
                "no_new_chapter": True,
                "paragraph_fits_on_page": True,
                "blockquote_fits_on_page": True,
                "table_row_continues": False,
            },
        )
        assert page_info.drop_page
        assert page_info.no_new_chapter
        assert page_info.paragraph_fits_on_page
        assert page_info.blockquote_fits_on_page
        assert page_info.table_row_continues is False

    def test_chapter_page(self):
        page_info = PageInfo.from_declaration(
            3,
            {"type": "chapter", "chapter_info": {"name": "Preamble"}},
        )
        assert page_info.is_chapter
        assert page_info.chapter_name == "Preamble"

    def test_type_other_than_chapter_is_kept(self):
        page_info = PageInfo.from_declaration(1, {"type": "illustration"})
        assert page_info.kind == "illustration"
        assert not page_info.is_chapter

    def test_chapter_info_of_a_page_that_is_not_a_chapter_is_not_checked(self):
        page_info = PageInfo.from_declaration(
            1, {"chapter_info": {"illumination_delimiter": "W"}}
        )
        assert not page_info.is_chapter
        assert page_info.chapter_name is None

    def test_chapter_page_without_chapter_info_is_rejected(self):
        with pytest.raises(ConverterError, match="Chapter page 4 missing chapter_info"):
            PageInfo.from_declaration(4, {"type": "chapter"})

    def test_chapter_page_without_name_is_rejected(self):
        with pytest.raises(
            ConverterError, match="Chapter page 4 missing name in chapter_info"
        ):
            PageInfo.from_declaration(4, {"type": "chapter", "chapter_info": {}})

    def test_single_typo_fix(self):
        page_info = PageInfo.from_declaration(
            1, {"typo_and_fix": {"typo": "teh", "fix": "the"}}
        )
        assert page_info.typo_fixes == (TypoFix("teh", "the"),)

    def test_list_of_typo_fixes_keeps_the_order(self):
        page_info = PageInfo.from_declaration(
            1,
            {
                "typo_and_fix": [
                    {"typo": "teh", "fix": "the"},
                    {"typo": "mnd", "fix": "mind"},
                ]
            },
        )
        assert page_info.typo_fixes == (TypoFix("teh", "the"), TypoFix("mnd", "mind"))

    @pytest.mark.parametrize("missing_key", ["typo", "fix"])
    def test_typo_fix_without_its_typo_or_its_fix_is_rejected(self, missing_key):
        fix_entry = {"typo": "teh", "fix": "the"}
        del fix_entry[missing_key]
        with pytest.raises(ConverterError, match=f"missing '{missing_key}'"):
            PageInfo.from_declaration(1, {"typo_and_fix": fix_entry})

    def test_unknown_key_is_rejected_whatever_the_page(self):
        # e.g. a misspelled "paragraph_fits_on_page" must not be silently ignored
        with pytest.raises(ConverterError, match="Page 7 declares unknown key"):
            PageInfo.from_declaration(7, {"paragraph_fit_on_page": True})

    def test_extra_key_declared_by_the_derived_class_is_accepted(self):
        page_info = PageInfo.from_declaration(
            1, {"header": True, "drop_page": True}, frozenset({"header"})
        )
        assert page_info.drop_page


class _DeclaringStructuralInfo(StructuralInfoBase):
    total_page_number = 5

    def __init__(self, declarations):
        super().__init__()
        self._declarations = declarations

    @property
    def pages_info(self) -> dict:
        return self._declarations


class _ExtraKeyStructuralInfo(_DeclaringStructuralInfo):
    EXTRA_PAGE_INFO_KEYS = frozenset({"header"})


class TestStructuralInfoBasePageInfo:
    def test_undeclared_page_gets_the_defaults(self):
        structural_info = _DeclaringStructuralInfo({1: {"drop_page": True}})
        assert structural_info.page_info(2) == PageInfo()

    def test_declared_page_is_read_through_page_info(self):
        structural_info = _DeclaringStructuralInfo(
            {
                1: {"drop_page": True},
                2: {"type": "chapter", "chapter_info": {"name": "Two"}},
                3: {"no_new_chapter": True},
            }
        )
        assert structural_info._page_is_dropped(1)
        assert not structural_info._page_is_dropped(2)
        assert structural_info._holds_new_chapter(2)
        assert not structural_info._holds_new_chapter(1)
        assert structural_info._forbids_new_chapter(3)
        assert not structural_info._forbids_new_chapter(2)

    def test_chapter_name_is_the_one_of_the_chapter_page(self):
        structural_info = _DeclaringStructuralInfo(
            {2: {"type": "chapter", "chapter_info": {"name": "Two"}}}
        )
        structural_info.set_chapter_page_number(3, 2)
        assert structural_info._get_chapter_name(3) == "Two"

    def test_a_wrong_declaration_fails_whichever_page_is_asked_for(self):
        structural_info = _DeclaringStructuralInfo({4: {"drop_pages": True}})
        with pytest.raises(ConverterError, match="Page 4 declares unknown key"):
            structural_info.page_info(0)

    def test_extra_key_of_the_derived_class_is_accepted(self):
        structural_info = _ExtraKeyStructuralInfo({1: {"header": True}})
        assert structural_info.page_info(1) == PageInfo()

    def test_extra_key_is_rejected_by_a_class_that_does_not_declare_it(self):
        structural_info = _DeclaringStructuralInfo({1: {"header": True}})
        with pytest.raises(ConverterError, match="unknown key"):
            structural_info.page_info(1)

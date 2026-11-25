"""DocumentBreaker validates the pages against the structural info upfront."""

import pytest

from pdf_to_markdown import ConverterError, Document

from .fixtures.fixture_structural_info import (
    FixtureConverter,
    FixtureStructuralInfo,
)
from .fixtures.generate_pdf import make_fixture_pdf


class _WrongPageCountStructuralInfo(FixtureStructuralInfo):
    @property
    def total_page_number(self) -> int:
        return 3


class _ChapterPageWithoutChapterInfoStructuralInfo(FixtureStructuralInfo):
    @property
    def pages_info(self) -> dict:
        return {0: {"type": "chapter"}}


class _ChapterPageWithoutNameStructuralInfo(FixtureStructuralInfo):
    @property
    def pages_info(self) -> dict:
        return {0: {"type": "chapter", "chapter_info": {}}}


@pytest.fixture
def pdf_path(tmp_path):
    path = tmp_path / "fixture.pdf"
    make_fixture_pdf(str(path))
    return path


def _convert(pdf_path, structural_info) -> Document:
    document = Document("Fixture Document")
    FixtureConverter(str(pdf_path), document, structural_info)
    return document


def test_valid_pages_are_accepted(pdf_path):
    document = _convert(pdf_path, FixtureStructuralInfo())
    assert len(document.get_chapters()) == 2


def test_each_page_knows_its_chapter(pdf_path):
    document = _convert(pdf_path, FixtureStructuralInfo())
    chapter_one, chapter_two = document.get_chapters()
    assert [
        (page.page_number, page.chapter_name, page.chapter_page_number)
        for page in chapter_one.pages
    ] == [(0, "Chapter One", 0), (1, "Chapter One", 0)]
    assert [
        (page.page_number, page.chapter_name, page.chapter_page_number)
        for page in chapter_two.pages
    ] == [(2, "Chapter Two", 2), (3, "Chapter Two", 2)]


def test_page_count_differing_from_the_declared_total_is_rejected(pdf_path):
    with pytest.raises(ConverterError, match="Erroneous number of pages"):
        _convert(pdf_path, _WrongPageCountStructuralInfo())


def test_chapter_page_without_chapter_info_is_rejected(pdf_path):
    with pytest.raises(ConverterError, match="Chapter page 0 missing chapter_info"):
        _convert(pdf_path, _ChapterPageWithoutChapterInfoStructuralInfo())


def test_chapter_page_without_name_is_rejected(pdf_path):
    with pytest.raises(
        ConverterError, match="Chapter page 0 missing name in chapter_info"
    ):
        _convert(pdf_path, _ChapterPageWithoutNameStructuralInfo())

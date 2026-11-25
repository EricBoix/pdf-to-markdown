"""A StructuralInfoBase can be used for several conversions, one after the other.

The configuration (pages_info ...) is the same from one conversion to the next,
whereas what a conversion produces along the way (the chapter of each page, the
tables cut out of the pages) belongs to that conversion only.
"""

import pytest

from pdf_to_markdown import Document, TableContent

from .fixtures.fixture_structural_info import (
    FixtureConverter,
    FixtureStructuralInfo,
)
from .fixtures.generate_pdf import make_fixture_pdf


@pytest.fixture
def pdf_path(tmp_path):
    path = tmp_path / "fixture.pdf"
    make_fixture_pdf(str(path))
    return path


def _convert(pdf_path, structural_info) -> Document:
    document = Document("Fixture Document")
    FixtureConverter(str(pdf_path), document, structural_info)
    return document


def test_same_structural_info_converts_twice_with_the_same_result(pdf_path):
    structural_info = FixtureStructuralInfo()
    first_document = _convert(pdf_path, structural_info)
    second_document = _convert(pdf_path, structural_info)
    assert [chapter.name for chapter in second_document.get_chapters()] == [
        chapter.name for chapter in first_document.get_chapters()
    ]
    assert [
        sentence.text
        for chapter in second_document.get_chapters()
        for paragraph in chapter.get_sublevels()
        for sentence in paragraph.get_sentences()
    ] == [
        sentence.text
        for chapter in first_document.get_chapters()
        for paragraph in chapter.get_sublevels()
        for sentence in paragraph.get_sentences()
    ]


def test_tables_of_a_conversion_are_not_left_for_the_next_one(pdf_path):
    structural_info = FixtureStructuralInfo()
    structural_info.table_registry.add(TableContent("Left over table", None, False))
    _convert(pdf_path, structural_info)
    assert structural_info.table_registry.get("Left over table") is None

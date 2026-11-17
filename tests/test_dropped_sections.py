"""Sections designated by the dropped_sections of a StructuralInfoBase."""

import pytest

from pdf_to_markdown import (
    ConverterError,
    Document,
    SectionDropper,
    SubChapterOfParagraphs,
    SuperChapter,
    TopLevelChapterOfParagraphs,
)

from .fixtures.fixture_structural_info import (
    FixtureConverter,
    FixtureStructuralInfo,
)
from .fixtures.generate_pdf import make_fixture_pdf


class _DroppingChapterTwoStructuralInfo(FixtureStructuralInfo):
    dropped_sections = ["chapter TWO"]


class _DroppingUnknownStructuralInfo(FixtureStructuralInfo):
    dropped_sections = ["No such section"]


class _DroppingNestedStructuralInfo(FixtureStructuralInfo):
    dropped_sections = ["Shared title"]


def _build_document(pdf_path, structural_info) -> Document:
    document = Document("Fixture Document")
    FixtureConverter(str(pdf_path), document, structural_info)
    return document


@pytest.fixture
def pdf_path(tmp_path):
    path = tmp_path / "fixture.pdf"
    make_fixture_pdf(str(path))
    return path


def test_default_drops_nothing(pdf_path):
    document = _build_document(pdf_path, FixtureStructuralInfo())
    assert [chapter.name for chapter in document.get_chapters()] == [
        "Chapter One",
        "Chapter Two",
    ]


def test_dropped_chapter_is_case_insensitive(pdf_path):
    document = _build_document(pdf_path, _DroppingChapterTwoStructuralInfo())
    chapters = document.get_chapters()
    assert [chapter.name for chapter in chapters] == ["Chapter One"]
    assert chapters[0].number == 1


def test_unmatched_dropped_section_raises(pdf_path):
    with pytest.raises(ConverterError):
        _build_document(pdf_path, _DroppingUnknownStructuralInfo())


def test_every_level_with_the_title_is_dropped_at_any_depth():
    document = Document("Nested")
    kept = SuperChapter("Kept")
    for title in ("Shared title", "Other"):
        kept.add_chapter(SubChapterOfParagraphs(title))
    document.add_chapter(kept)
    document.add_chapter(TopLevelChapterOfParagraphs("Shared title"))

    SectionDropper(_DroppingNestedStructuralInfo()).drop_sections(document)

    assert [chapter.name for chapter in document.get_chapters()] == ["Kept"]
    assert [chapter.name for chapter in kept.get_chapters()] == ["Other"]
    assert kept.get_chapters()[0].number == 1

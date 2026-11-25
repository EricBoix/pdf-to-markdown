"""End-to-end pipeline on a document made of super chapters.

The 5-page fixture PDF (see generate_pdf.make_superchapter_fixture_pdf) is run
through a DocumentWithSubChapters: each super chapter is broken into numbered
sub-chapters, each sub-chapter into paragraphs and sentences.
"""

import pytest

from pdf_to_markdown import (
    DocumentWithSubChapters,
    SubChapterOfParagraphs,
    SuperChapter,
)

from .fixtures.fixture_structural_info import build_superchapter_fixture_document
from .fixtures.generate_pdf import make_superchapter_fixture_pdf


@pytest.fixture
def superchapter_document(tmp_path):
    pdf_path = tmp_path / "superchapter_fixture.pdf"
    make_superchapter_fixture_pdf(str(pdf_path))
    return build_superchapter_fixture_document(str(pdf_path))


def _sentences_of(sub_chapter):
    return [
        sentence
        for paragraph in sub_chapter.get_sublevels()
        for sentence in paragraph.get_sentences()
    ]


def test_document_holds_two_super_chapters(superchapter_document):
    assert isinstance(superchapter_document, DocumentWithSubChapters)
    super_chapters = superchapter_document.get_chapters()
    assert all(isinstance(chapter, SuperChapter) for chapter in super_chapters)
    assert [chapter.name for chapter in super_chapters] == ["Part One", "Part Two"]


def test_super_chapters_are_broken_into_numbered_sub_chapters(superchapter_document):
    first_part, second_part = superchapter_document.get_chapters()
    assert all(
        isinstance(sub_chapter, SubChapterOfParagraphs)
        for sub_chapter in first_part.get_sublevels() + second_part.get_sublevels()
    )
    assert [sub_chapter.name for sub_chapter in first_part.get_sublevels()] == [
        "Alpha",
        "Beta",
    ]
    assert [sub_chapter.number for sub_chapter in first_part.get_sublevels()] == [1, 2]
    assert [sub_chapter.name for sub_chapter in second_part.get_sublevels()] == [
        "Gamma"
    ]
    assert [sub_chapter.number for sub_chapter in second_part.get_sublevels()] == [1]


def test_sub_chapters_are_broken_into_sentences(superchapter_document):
    first_part, second_part = superchapter_document.get_chapters()
    alpha, beta = first_part.get_sublevels()
    gamma = second_part.get_sublevels()[0]
    assert [sentence.text for sentence in _sentences_of(alpha)] == [
        "First alpha sentence.",
        "Second alpha sentence.",
    ]
    assert [sentence.text for sentence in _sentences_of(beta)] == ["Beta sentence."]
    assert [sentence.text for sentence in _sentences_of(gamma)] == ["Gamma sentence."]


def test_sentences_keep_the_pdf_page_index_they_come_from(superchapter_document):
    first_part, second_part = superchapter_document.get_chapters()
    alpha, beta = first_part.get_sublevels()
    gamma = second_part.get_sublevels()[0]
    assert [sentence.page_layout.page_number for sentence in _sentences_of(alpha)] == [
        1,
        1,
    ]
    assert [sentence.page_layout.page_number for sentence in _sentences_of(beta)] == [2]
    assert [sentence.page_layout.page_number for sentence in _sentences_of(gamma)] == [
        4
    ]

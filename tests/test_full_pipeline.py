"""End-to-end pipeline tests.

A minimal 4-page PDF is generated at test time (no binary committed to git).
The fixture exercises all pipeline-stage contexts in a single run:
  - Chapter-name normalization (pages 0 and 2)
  - Sentence splitting with quote preservation (page 1)
  - Plain paragraph baseline (page 3)
"""

import pytest

from .fixtures.generate_pdf import make_fixture_pdf
from .fixtures.fixture_structural_info import build_fixture_document


@pytest.fixture
def fixture_document(tmp_path):
    pdf_path = tmp_path / "fixture.pdf"
    make_fixture_pdf(str(pdf_path))
    return build_fixture_document(str(pdf_path))


def test_two_chapters_detected(fixture_document):
    chapters = fixture_document.get_chapters()
    assert len(chapters) == 2


def test_chapter_names(fixture_document):
    chapters = fixture_document.get_chapters()
    assert chapters[0].name == "Chapter One"
    assert chapters[1].name == "Chapter Two"


def test_chapter_one_has_one_paragraph(fixture_document):
    chapters = fixture_document.get_chapters()
    paragraphs = chapters[0].get_sublevels()
    assert paragraphs is not None
    assert len(paragraphs) == 1


def test_chapter_one_paragraph_splits_into_two_sentences(fixture_document):
    chapters = fixture_document.get_chapters()
    sentences = chapters[0].get_sublevels()[0].get_sentences()
    assert len(sentences) == 2


def test_chapter_one_sentences_boundary_apostrophes_unchanged(fixture_document):
    chapters = fixture_document.get_chapters()
    sentences = chapters[0].get_sublevels()[0].get_sentences()
    assert sentences[0].text == "'It is overfull."
    assert sentences[1].text == "No more will go in!'"


def test_chapter_two_has_one_sentence(fixture_document):
    chapters = fixture_document.get_chapters()
    sentences = chapters[1].get_sublevels()[0].get_sentences()
    assert len(sentences) == 1
    assert sentences[0].text == "Correct sentences are valuable."

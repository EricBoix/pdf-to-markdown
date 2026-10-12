"""Tests for the in-memory document-model operations.

These tests exercise the data-structure layer (PageLayout, Sentence, Paragraph,
DocumentHierarchicalLevel hierarchy) without any I/O or text-transformation
logic.
"""

import pytest
from mdutils.mdutils import MdUtils

from pdf_to_markdown import (
    Document,
    PageLayout,
    Paragraph,
    Sentence,
    TopLevelChapterOfParagraphs,
)


class TestPageLayout:
    def test_int_reader_page_number_stored(self):
        layout = PageLayout(42, 10)
        assert layout.reader_page_number == 42
        assert layout.page_number == 10

    def test_str_reader_page_number_stored(self):
        layout = PageLayout("xii", 5)
        assert layout.reader_page_number == "xii"
        assert layout.page_number == 5

    def test_copy_is_independent(self):
        layout = PageLayout(1, 0)
        copy = layout.__copy__()
        assert copy.reader_page_number == layout.reader_page_number
        assert copy.page_number == layout.page_number
        # Modifying the copy does not affect the original.
        copy._reader_page_number = 99
        assert layout.reader_page_number == 1


class TestSentence:
    def _layout(self):
        return PageLayout(1, 0)

    def test_text_stored(self):
        sentence = Sentence("Hello world.", self._layout())
        assert sentence.text == "Hello world."

    def test_append_joins_with_space(self):
        sentence = Sentence("First part", self._layout())
        other = Sentence("second part.", self._layout())
        sentence.append(other)
        assert sentence.text == "First part second part."

    def test_is_complete_true_for_grammatical_sentence(self):
        sentence = Sentence("The monk walked slowly.", self._layout())
        assert sentence.is_complete() is True

    def test_is_complete_false_no_capital(self):
        sentence = Sentence("no capital letter.", self._layout())
        assert sentence.is_complete() is False

    def test_is_complete_false_no_punctuation(self):
        sentence = Sentence("Missing punctuation", self._layout())
        assert sentence.is_complete() is False

    def test_is_complete_false_no_verb(self):
        # A noun phrase with capital letter and punctuation but no verb.
        sentence = Sentence("The blue sky.", self._layout())
        assert sentence.is_complete() is False


class TestDocumentHierarchicalLevel:
    def _chapter_with_doc(self):
        doc = Document("Test")
        chapter = TopLevelChapterOfParagraphs("Chapter")
        doc.add_chapter(chapter)
        return chapter

    def _para(self, page_number=0):
        return Paragraph(PageLayout(page_number + 1, page_number))

    def test_add_sublevel_sets_parent_back_ref(self):
        chapter = self._chapter_with_doc()
        para = self._para()
        chapter.add_sublevel(para)
        assert para.owning_hierarchical_level is chapter

    def test_renumber_sublevels_produces_one_based_indices(self):
        chapter = self._chapter_with_doc()
        for page_number in range(3):
            chapter.add_sublevel(self._para(page_number))
        chapter.renumber_sublevels()
        for index, sublevel in enumerate(chapter.get_sublevels(), start=1):
            assert sublevel.number == index

    def test_remove_sublevel_decreases_count(self):
        chapter = self._chapter_with_doc()
        para = self._para()
        chapter.add_sublevel(para)
        assert len(chapter.get_sublevels()) == 1
        chapter.remove_sublevel(para)
        assert chapter.get_sublevels() is None or len(chapter.get_sublevels()) == 0

    def test_remove_absent_sublevel_raises(self):
        chapter = self._chapter_with_doc()
        para = self._para()
        chapter.add_sublevel(para)
        other = self._para()
        with pytest.raises(ValueError):
            chapter.remove_sublevel(other)

    def test_merge_combines_sentences_and_removes_other(self):
        chapter = self._chapter_with_doc()
        layout_0 = PageLayout(1, 0)
        layout_1 = PageLayout(2, 1)
        para1 = Paragraph(layout_0)
        para2 = Paragraph(layout_1)
        chapter.add_sublevel(para1)
        chapter.add_sublevel(para2)
        para1.add_sublevel(Sentence("First.", layout_0))
        para2.add_sublevel(Sentence("Second.", layout_1))

        para1.merge(para2)

        assert len(para1.get_sentences()) == 2
        assert len(chapter.get_sublevels()) == 1
        assert chapter.get_sublevels()[0] is para1


class TestParagraphToMarkdown:
    def test_sentences_joined_into_paragraph(self, tmp_path):
        layout = PageLayout(1, 0)
        para = Paragraph(layout)
        para.add_sublevel(Sentence("First sentence.", layout))
        para.add_sublevel(Sentence("Second sentence.", layout))

        md = MdUtils(file_name=str(tmp_path / "test"), title="Test")
        para.to_markdown(md, 2)

        assert "First sentence." in md.file_data_text
        assert "Second sentence." in md.file_data_text

"""The typographic rules deciding whether the text starting a page continues the
paragraph that ends the previous one (see ParagraphMerger._continues)."""

import logging

import pytest

from pdf_to_markdown import (
    ExtractedPage,
    PageLayout,
    Paragraph,
    ParagraphMerger,
    Sentence,
    StructuralInfoBase,
    TopLevelChapterOfParagraphs,
)
from pdf_to_markdown.typo_rules import (
    CompleteHeadUppercaseTailStartsParagraph,
    LowercaseTailContinues,
    TypoRuleVerdict,
    UnpunctuatedHeadContinues,
)

from .fixtures.fixture_structural_info import DeclaresTheMergeRules


def _sentence(text, page_number=1):
    return Sentence(text, PageLayout(page_number + 1, page_number))


class _StructuralInfo(DeclaresTheMergeRules, StructuralInfoBase):
    pages_info = {}
    total_page_number = 3
    numbered_list_heuristics_enabled = False

    def _holds_new_chapter(self, page_number):
        return False


class _StructuralInfoDeclaringNoRule(StructuralInfoBase):
    pages_info = {}
    total_page_number = 3
    numbered_list_heuristics_enabled = False

    def _holds_new_chapter(self, page_number):
        return False


def _merger(structural_info_class=_StructuralInfo):
    return ParagraphMerger(structural_info_class())


class TestContinues:
    @pytest.mark.parametrize(
        "head_text,tail_text,expected",
        [
            # Terminal punctuation variants of a complete head: an uppercase tail
            # starts a new paragraph
            ("It ends.", "Next starts.", False),
            ("It ends.11", "Next starts.", False),
            ("It ends!", "Next starts.", False),
            ("Does it end?", "Next starts.", False),
            ('He said "it ends."', "Next starts.", False),
            ("It ends (really.)", "Next starts.", False),
            ("The mind is there...", "Next starts.", False),
            # A head without terminal punctuation continues
            ("It goes on and", "on to the next page.", True),
            ("It goes on and", "On the next page.", True),
            ("It lasted for 11", "years.", True),
            # A lowercase tail continues, even after a complete head
            ("It ends.", "and goes on.", True),
            # Neither lowercase nor uppercase tail after a complete head: no rule
            # decides, the answer is no
            ("It ends.", "1. A list item.", False),
        ],
    )
    def test_decision(self, head_text, tail_text, expected):
        assert (
            _merger()._continues(_sentence(head_text), _sentence(tail_text, 2))
            is expected
        )

    def test_nothing_continues_when_the_document_declares_no_rule(self):
        merger = _merger(_StructuralInfoDeclaringNoRule)
        assert not merger._continues(
            _sentence("It goes on and"), _sentence("on to the next page.", 2)
        )


class TestMergeRulesVerdicts:
    def test_lowercase_tail_continues(self):
        rule = LowercaseTailContinues()
        assert (
            rule.verdict(_sentence("It ends."), _sentence("and goes on."))
            is TypoRuleVerdict.CONTINUES
        )
        assert (
            rule.verdict(_sentence("It ends."), _sentence("Next."))
            is TypoRuleVerdict.NO_OPINION
        )

    def test_unpunctuated_head_continues(self):
        rule = UnpunctuatedHeadContinues()
        assert (
            rule.verdict(_sentence("It goes on and"), _sentence("Next."))
            is TypoRuleVerdict.CONTINUES
        )
        assert (
            rule.verdict(_sentence("It ends.12"), _sentence("and on."))
            is TypoRuleVerdict.NO_OPINION
        )

    def test_complete_head_uppercase_tail_starts_a_paragraph(self):
        rule = CompleteHeadUppercaseTailStartsParagraph()
        assert (
            rule.verdict(_sentence("It ends."), _sentence("Next."))
            is TypoRuleVerdict.NEW_PARAGRAPH
        )
        assert (
            rule.verdict(_sentence("It goes on and"), _sentence("Next."))
            is TypoRuleVerdict.NO_OPINION
        )


class TestTraps:
    def test_lowercase_tail_after_a_complete_head_is_contradicting(self):
        rule = LowercaseTailContinues()
        assert rule.contradicted_by(_sentence("It ends."), _sentence("and on."))
        assert not rule.contradicted_by(
            _sentence("It goes on and"), _sentence("on to.")
        )

    def test_uppercase_tail_after_an_unpunctuated_head_is_contradicting(self):
        rule = UnpunctuatedHeadContinues()
        assert rule.contradicted_by(_sentence("It goes on and"), _sentence("Next."))
        assert not rule.contradicted_by(
            _sentence("It goes on and"), _sentence("on to.")
        )

    def test_a_contradicting_page_break_is_warned_about(self, caplog):
        with caplog.at_level(logging.WARNING, logger="pdf_to_markdown"):
            _merger()._continues(
                _sentence("It goes on and"), _sentence("Next starts.", 2)
            )
        assert "UnpunctuatedHeadContinues" in caplog.text
        assert "contradicts it" in caplog.text

    def test_an_undeclared_rule_is_not_trapped(self, caplog):
        with caplog.at_level(logging.WARNING, logger="pdf_to_markdown"):
            _merger(_StructuralInfoDeclaringNoRule)._continues(
                _sentence("It goes on and"), _sentence("Next starts.", 2)
            )
        assert caplog.text == ""

    def test_supported_page_break(self):
        assert UnpunctuatedHeadContinues().supported_by(
            _sentence("It goes on and"), _sentence("on to.")
        )
        assert not UnpunctuatedHeadContinues().supported_by(
            _sentence("It goes on and"), _sentence("Next.")
        )


def _paragraph(page_number, *sentence_texts):
    paragraph = Paragraph(PageLayout(page_number + 1, page_number))
    for sentence_text in sentence_texts:
        paragraph.add_sublevel(_sentence(sentence_text, page_number))
    paragraph.renumber_sublevels()
    return paragraph


def _merge(head_text, tail_text):
    chapter = TopLevelChapterOfParagraphs("Chapter")
    for page_number in (1, 2):
        chapter.add_page(
            ExtractedPage(page_number, PageLayout(page_number + 1, page_number), None)
        )
    head, tail = _paragraph(1, head_text), _paragraph(2, tail_text)
    chapter.add_sublevel(head)
    chapter.add_sublevel(tail)
    chapter.renumber_sublevels()
    _merger().reconstitute_paragraphs_spreading_over_two_pages(chapter)
    return chapter.get_sublevels()


class TestParagraphsAcrossAPageBreak:
    def test_a_footnote_number_after_the_punctuation_does_not_make_the_head_incomplete(
        self,
    ):
        # Regression: "...colored marks.2" then an indented paragraph starting
        # with an uppercase letter is a new paragraph, not a continuation.
        sublevels = _merge(
            "It is shown with colored marks.2", "While this model differs."
        )
        assert len(sublevels) == 2

    def test_a_sentence_cut_by_the_page_break_is_reconstituted(self):
        sublevels = _merge("The mind settles into", "a deep peace.")
        assert len(sublevels) == 1
        assert sublevels[0].get_sentences()[0].text == (
            "The mind settles into a deep peace."
        )

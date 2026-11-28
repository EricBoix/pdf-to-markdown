"""The rules folding characters to ASCII: held by a document, or not."""

from unittest.mock import MagicMock

from pdf_to_markdown import StructuralInfoBase, TextExtractor, TextSanitizer
from pdf_to_markdown.typo_rules import (
    DiacriticsFoldToBaseLetters,
    SmileyGlyphsFoldToAnEmoticon,
)


class TestDiacriticsFoldToBaseLetters:
    def test_the_default_letters_fold_to_their_base_letter(self):
        assert DiacriticsFoldToBaseLetters().fold("Paññā, ṭhāna") == "Panna, thana"

    def test_a_book_declares_the_letters_it_needs(self):
        rule = DiacriticsFoldToBaseLetters({"é": "e"})
        assert rule.fold("café ñ") == "cafe ñ"

    def test_the_characters_left_unfolded_are_listed(self):
        assert DiacriticsFoldToBaseLetters.unfolded_characters("a é b ø") == [
            "é",
            "ø",
        ]


class TestSmileyGlyphsFoldToAnEmoticon:
    def test_both_glyphs_fold_to_an_emoticon(self):
        assert SmileyGlyphsFoldToAnEmoticon().fold("a \u263a b \uf04a") == "a :-) b :-)"


class TestSanitizeCharacters:
    def test_the_quotes_and_dashes_are_folded_whatever_the_rules(self):
        assert TextSanitizer.sanitize_characters("“a” — b") == '"a" -- b'

    def test_the_diacritics_are_left_alone_without_the_rule(self):
        assert TextSanitizer.sanitize_characters("Paññā") == "Paññā"


class _StructuralInfo(StructuralInfoBase):
    pages_info = {}
    total_page_number = 1
    valid_rules = frozenset({"DiacriticsFoldToBaseLetters"})


class TestDeclaredByTheDocument:
    def test_only_the_rules_that_hold_are_given_to_the_code(self):
        names = [rule.name for rule in _StructuralInfo().character_folding_rules()]
        assert names == ["DiacriticsFoldToBaseLetters"]

    def test_the_document_declares_its_letters(self):
        class _WithItsLetters(_StructuralInfo):
            diacritic_foldings = {"é": "e"}

        (rule,) = _WithItsLetters().character_folding_rules()
        assert rule.fold("café ñ") == "cafe ñ"


class TestTrap:
    def test_a_character_no_folding_covers_is_reported_with_its_page(self, caplog):
        page = MagicMock()
        page.extract_text.return_value = "a \u00f8 b"
        reader = MagicMock()
        reader.pages = [page]
        structural_info = _StructuralInfo()
        structural_info.strip_page_text_leading_whitespace = lambda text: text
        structural_info._page_is_dropped = lambda page_number: False
        with caplog.at_level("WARNING", logger="pdf_to_markdown"):
            TextExtractor(reader, structural_info).extract_all()
        assert "DiacriticsFoldToBaseLetters" in caplog.text
        assert "page 0" in caplog.text

from .TypoRuleForCharacters import TypoRuleForCharacters


class SmileyGlyphsFoldToAnEmoticon(TypoRuleForCharacters):
    """The white smiling face and the private-use glyph of some PDF fonts both
    stand for a smiley, folded to the ASCII emoticon ":-)".

    U+F04A is a font artefact: its meaning depends on the font of the book,
    hence the rule is declared by the book. Action site:
    TextExtractor.extract_all, through TextSanitizer.sanitize_characters.
    """

    FOLDINGS = {
        "\u263a": ":-)",  # U+263A WHITE SMILING FACE
        "\uf04a": ":-)",  # U+F04A private-use smiling face (PDF font glyph)
    }

    def fold(self, text: str) -> str:
        for glyph, emoticon in self.FOLDINGS.items():
            text = text.replace(glyph, emoticon)
        return text

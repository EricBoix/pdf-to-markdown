from typing import Mapping

from .TypoRuleForCharacters import TypoRuleForCharacters


class DiacriticsFoldToBaseLetters(TypoRuleForCharacters):
    """The letters carrying a diacritic that a book uses (e.g. the transliteration
    of a language) fold to the closest ASCII base letter.

    The letters are those the book declares (StructuralInfoBase.
    diacritic_foldings, whose default is DEFAULT_FOLDINGS). Action site:
    TextExtractor.extract_all, through TextSanitizer.sanitize_characters.
    Trap: a character that no folding covers is left as it is, and reported
    with its page (TextExtractor), instead of passing silently.
    """

    # Pali transliteration uses several extended Latin characters that have no
    # ASCII counterpart. Each is folded to the closest ASCII base letter.
    DEFAULT_FOLDINGS: Mapping[str, str] = {
        "\u00f1": "n",  # U+00F1 LATIN SMALL LETTER N WITH TILDE -> U+006E ASCII LATIN SMALL LETTER N
        "\u0101": "a",  # U+0101 LATIN SMALL LETTER A WITH MACRON -> U+0061 ASCII LATIN SMALL LETTER A
        "\u012b": "i",  # U+012B LATIN SMALL LETTER I WITH MACRON -> U+0069 ASCII LATIN SMALL LETTER I
        "\u1e37": "l",  # U+1E37 LATIN SMALL LETTER L WITH DOT BELOW -> U+006C ASCII LATIN SMALL LETTER L
        "\u1e43": "m",  # U+1E43 LATIN SMALL LETTER M WITH DOT BELOW -> U+006D ASCII LATIN SMALL LETTER M
        "\u1e47": "n",  # U+1E47 LATIN SMALL LETTER N WITH DOT BELOW -> U+006E ASCII LATIN SMALL LETTER N
        "\u1e6d": "t",  # U+1E6D LATIN SMALL LETTER T WITH DOT BELOW -> U+0074 ASCII LATIN SMALL LETTER T
        "\u0100": "A",  # U+0100 LATIN CAPITAL LETTER A WITH MACRON -> U+0041 ASCII LATIN CAPITAL LETTER A
        "\u012a": "I",  # U+012A LATIN CAPITAL LETTER I WITH MACRON -> U+0049 ASCII LATIN CAPITAL LETTER I
        "\u015a": "S",  # U+015A LATIN CAPITAL LETTER S WITH ACUTE -> U+0053 ASCII LATIN CAPITAL LETTER S
        "\u015b": "s",  # U+015B LATIN SMALL LETTER S WITH ACUTE -> U+0073 ASCII LATIN SMALL LETTER S
        "\u016b": "u",  # U+016B LATIN SMALL LETTER U WITH MACRON -> U+0075 ASCII LATIN SMALL LETTER U
        "\u1e45": "n",  # U+1E45 LATIN SMALL LETTER N WITH DOT ABOVE -> U+006E ASCII LATIN SMALL LETTER N
        "\u1e63": "s",  # U+1E63 LATIN SMALL LETTER S WITH DOT BELOW -> U+0073 ASCII LATIN SMALL LETTER S
        "\u1e0d": "d",  # U+1E0D LATIN SMALL LETTER D WITH DOT BELOW -> U+0064 ASCII LATIN SMALL LETTER D
        "\u1e5b": "r",  # U+1E5B LATIN SMALL LETTER R WITH DOT BELOW -> U+0072 ASCII LATIN SMALL LETTER R
        "\u1e25": "h",  # U+1E25 LATIN SMALL LETTER H WITH DOT BELOW -> U+0068 ASCII LATIN SMALL LETTER H
    }

    def __init__(self, foldings: Mapping[str, str] | None = None) -> None:
        self._foldings = dict(self.DEFAULT_FOLDINGS if foldings is None else foldings)

    def fold(self, text: str) -> str:
        for character, base_letter in self._foldings.items():
            text = text.replace(character, base_letter)
        return text

    @staticmethod
    def unfolded_characters(text: str) -> list[str]:
        """The non ASCII characters that are left in the text (once folded)."""
        return sorted({character for character in text if not character.isascii()})

import re

from ..Model import Paragraph
from ..TextSanitizer import TextSanitizer
from .TypoRule import TypoRule


class BlockquoteRepeatingParagraphIsDropped(TypoRule):
    """A pull quote that merely repeats the text of a paragraph is dropped, the
    paragraph of the running text being the one that is kept.

    A pull quote of a book page is sometimes an exact copy of a few sentences of
    the running text (the other pull quotes are paraphrases that carry their own
    content and are thus kept). A blockquote is a duplicate when, up to
    normalization, its text is made of one or more consecutive *complete*
    sentences of a paragraph: the match must start and end on sentence
    boundaries of the paragraph (a prefix of the paragraph, sentences in its
    middle, or the whole paragraph) so that a blockquote is never dropped just
    because its words happen to be part of a longer sentence.

    The rule removes text from the document. Action site:
    BlockquoteDeduplicator. Trap: each dropped blockquote is reported with its
    page.
    """

    @staticmethod
    def normalize(text: str) -> str:
        """Text that only differs by whitespace (e.g. line folding, hyphenation
        artifacts such as "non- perceiving") or typographic characters
        (quotes, dashes...) normalizes to the same value.

        The sentences that come out of a pdf are ASCII already (see
        TextExtractor). Those of a document that was not extracted from a pdf
        (see MarkdownToDocument) keep their typographic characters."""
        return re.sub(r"\s+", "", TextSanitizer.sanitize_characters(text))

    def is_made_of_whole_sentences(
        self, normalized_blockquote: str, paragraph: Paragraph
    ) -> bool:
        """Whether the (normalized) text is made of consecutive whole sentences
        of the paragraph."""
        normalized_sentences = [
            self.normalize(sentence.text) for sentence in paragraph.get_sentences()
        ]
        for first_index in range(len(normalized_sentences)):
            accumulated_text = ""
            for sentence_text in normalized_sentences[first_index:]:
                accumulated_text += sentence_text
                if accumulated_text == normalized_blockquote:
                    return True
                if not normalized_blockquote.startswith(accumulated_text):
                    break
        return False

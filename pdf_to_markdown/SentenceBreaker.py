import nltk

from .TextSanitizer import TextSanitizer


class SentenceBreaker:
    """Breaks the text of a paragraph into its sentences.

    The text is expected to be plain ASCII already, with its ellipses spelled
    "..." (that is what the TextExtractor produces, see there). The sentences
    come out with their newlines and multiple whitespaces collapsed, and those
    holding an ambiguous apostrophe framed (see
    TextSanitizer.frame_sentences_if_unbalanced).

    Only the text given is needed: nothing of the document tree, nor of a
    structural information. The breaker can thus be used wherever text has to
    be cut into the sentences that the document model holds.
    """

    @staticmethod
    def break_into_sentences(paragraph_text: str) -> list[str]:
        """The (non empty) sentences of the text of a paragraph, in order."""
        sentences = [
            TextSanitizer.normalize_newlines_and_multiple_whitespaces(sentence)
            for sentence in nltk.tokenize.sent_tokenize(paragraph_text)
            if sentence
        ]
        # Boundary apostrophes from sentence splitting are preserved as-is.
        # They are meaningful fragments of the original quotation and must not
        # be stripped or re-injected. See TextSanitizer.frame_sentences_if_unbalanced
        # for the full rationale.
        framed_sentences = TextSanitizer.frame_sentences_if_unbalanced(sentences)
        return [sentence for sentence in framed_sentences if sentence]

import re

from .Model import (
    BlockQuoteParagraph,
    DocumentHierarchicalLevel,
    Paragraph,
)
from .DiagnosticsReporter import DiagnosticsReporter
from .TextSanitizer import TextSanitizer


class BlockquoteDeduplicator:
    """Drops the blockquotes that merely repeat the text of a paragraph.

    A pull quote of a book page is sometimes an exact copy of a few sentences
    of the running text (the other pull quotes are paraphrases that carry their
    own content and are thus kept). Such a repeated blockquote is dropped, the
    paragraph of the running text being the one that is kept.

    A blockquote is a duplicate when, up to normalization, its text is made of
    one or more consecutive *complete* sentences of a paragraph. That is, the
    match must start and end on sentence boundaries of the paragraph (this
    covers a prefix of the paragraph, sentences in its middle, and the whole
    paragraph) so that a blockquote is never dropped just because its words
    happen to be part of a longer sentence. Sentences of the blockquote itself
    are not required to be tokenized like the ones of the paragraph: only the
    concatenation of their text counts.

    The paragraph must be found on the page of the blockquote, on its previous
    page or on its next page (and nowhere else). Blockquotes are only compared
    to paragraphs, never to other blockquotes.

    This is meant to be applied once the paragraphs spreading over two pages
    were reconstituted (see ParagraphMerger).
    """

    def __init__(self, diagnostics: DiagnosticsReporter | None = None) -> None:
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)

    @staticmethod
    def _normalize(text: str) -> str:
        """Text that only differs by whitespace (e.g. line folding, hyphenation
        artifacts such as "non- perceiving") or typographic characters
        (quotes, dashes...) normalizes to the same value."""
        return re.sub(r"\s+", "", TextSanitizer.sanitize_characters(text))

    def _collect_paragraphs(self, level: DocumentHierarchicalLevel) -> list[Paragraph]:
        paragraphs = []
        for sublevel in level.get_sublevels() or []:
            if isinstance(sublevel, Paragraph):
                paragraphs.append(sublevel)
            elif isinstance(sublevel, DocumentHierarchicalLevel):
                paragraphs += self._collect_paragraphs(sublevel)
        return paragraphs

    @staticmethod
    def _get_page_numbers(paragraph: Paragraph) -> set[int]:
        """Pages on which a paragraph lies (more than one when it spreads over
        two pages)."""
        page_numbers = {paragraph.page_layout.page_number}
        for sentence in paragraph.get_sentences() or []:
            page_numbers.add(sentence.page_layout.page_number)
        return page_numbers

    def _is_made_of_whole_sentences(
        self, normalized_blockquote: str, paragraph: Paragraph
    ) -> bool:
        normalized_sentences = [
            self._normalize(sentence.text) for sentence in paragraph.get_sentences()
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

    def remove_duplicated_blockquotes(self, document) -> None:
        paragraphs = []
        for chapter in document.get_chapters():
            paragraphs += self._collect_paragraphs(chapter)

        candidates_per_page: dict[int, list[Paragraph]] = {}
        for paragraph in paragraphs:
            if isinstance(paragraph, BlockQuoteParagraph):
                continue
            if not paragraph.get_sentences():
                continue
            for page_number in self._get_page_numbers(paragraph):
                candidates_per_page.setdefault(page_number, []).append(paragraph)

        duplicated_blockquotes = []
        for blockquote in paragraphs:
            if not isinstance(blockquote, BlockQuoteParagraph):
                continue
            if not blockquote.get_sentences():
                continue
            normalized_blockquote = self._normalize(
                "".join(sentence.text for sentence in blockquote.get_sentences())
            )
            if not normalized_blockquote:
                continue
            blockquote_page_number = blockquote.page_layout.page_number
            for page_number in (
                blockquote_page_number - 1,
                blockquote_page_number,
                blockquote_page_number + 1,
            ):
                if any(
                    self._is_made_of_whole_sentences(normalized_blockquote, paragraph)
                    for paragraph in candidates_per_page.get(page_number, [])
                ):
                    duplicated_blockquotes.append(blockquote)
                    break

        for blockquote in duplicated_blockquotes:
            self._diagnostics.debug(
                f"Dropping blockquote duplicating a paragraph: "
                f"{blockquote.get_document_reference_long()}"
            )
            parent = blockquote.owning_hierarchical_level
            parent.remove_sublevel(blockquote)
            parent.renumber_sublevels()

from .Model import (
    BlockQuoteParagraph,
    Paragraph,
    Table,
    Heading,
    TopLevelChapter,
)
from .DiagnosticsReporter import DiagnosticsReporter
from .NumberedListAnnotator import NumberedListAnnotator
from .Errors import ConverterError
from .Model import Sentence
from .typo_rules import TypoRuleForMerge, TypoRuleVerdict


class ParagraphMerger:
    """Handles merging of paragraphs that span across page boundaries.

    Blockquotes (e.g. the pull quotes of a book page) are ignored when looking
    for "the first/last paragraph of a page". A blockquote is a floating box
    placed on the page: it is not part of the running text that flows from the
    bottom of a page to the top of the next one. When a blockquote happens to
    be the last (resp. first) element of a page, selecting it would break the
    reconstitution of a paragraph that spreads over two pages:
    - as the last element of its page: the blockquote (that usually ends with a
      complete sentence) would be taken for the end of the page, no merge would
      be attempted, and the paragraph cut by the page break would stay in two
      pieces;
    - as the first element of its page: the blockquote would be merged as if it
      was the continuation of the unfinished sentence of the previous page.
    Skipping blockquotes on both sides keeps the text flow intact.
    """

    def __init__(
        self, structural_info, diagnostics: DiagnosticsReporter | None = None
    ) -> None:
        self.structural_info = structural_info
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)
        # The rules come from the rule register of the structural information
        self._merge_rules: list[TypoRuleForMerge] = (
            structural_info.rule_register.merge_rules()
        )

    def _continues(self, head: Sentence, tail: Sentence) -> bool:
        """Whether the tail (the first sentence of a page) continues the head (the
        last sentence of the page before), according to the typographic rules the
        structural info declares to hold.

        The rules are asked in order, the first verdict that is not NO_OPINION
        decides. When no declared rule decides the answer is no: a false split
        leaves a paragraph in two pieces, a false merge glues a sentence onto
        another page (a design preference, not a rule). The declared rules are also
        asked whether the page break contradicts them (a warning, see
        TypoRuleForMerge.contradicted_by).
        """
        holding_rules = [
            rule
            for rule in self._merge_rules
            if self.structural_info.rule_holds(rule.name)
        ]
        for rule in holding_rules:
            if rule.contradicted_by(head, tail):
                self._diagnostics.warn(
                    f"The rule {rule.name} is declared to hold but the page break "
                    f"between page {head.page_layout.page_number} "
                    f"(ends with: {head.text[-60:]!r}) and page "
                    f"{tail.page_layout.page_number} "
                    f"(starts with: {tail.text[:60]!r}) contradicts it."
                )
        for rule in holding_rules:
            verdict = rule.verdict(head, tail)
            if verdict is not TypoRuleVerdict.NO_OPINION:
                return verdict is TypoRuleVerdict.CONTINUES
        return False

    def _page_requires_paragraph_continuation(self, page_number: int) -> bool:
        # A page that declares nothing requires the continuation (looks a bit
        # ambitious but let's try it)
        return not self.structural_info.page_info(page_number).paragraph_fits_on_page

    def _page_requires_blockquote_continuation(self, page_number: int) -> bool:
        return not self.structural_info.page_info(page_number).blockquote_fits_on_page

    def _page_breaks_to_mend(self, top_level_chapter, page_requires_continuation):
        """The page breaks of a top level chapter that may have cut an element
        in two, in order, as (page number, number of the page that continues it).

        A page that does not require a continuation (it is flagged as such by
        the structural info) opens no page break, and neither does a page
        followed by a new chapter. The pages that the structural info skips are
        left aside: the page that continues is the first one not skipped.
        """
        if not isinstance(top_level_chapter, TopLevelChapter):
            return
        for page_index in range(0, len(top_level_chapter.pages) - 1):
            page_number = top_level_chapter.pages[page_index].page_number
            if not page_requires_continuation(page_number):
                continue
            next_page_number = (
                self.structural_info._get_page_number_finishing_last_paragraph(
                    page_number
                )
            )
            if self.structural_info._holds_new_chapter(next_page_number):
                continue
            yield page_number, next_page_number

    @staticmethod
    def _paragraphs_of_page(
        top_level_chapter, page_number: int, blockquotes_included: bool
    ) -> list[Paragraph]:
        """The paragraphs lying on a page, in reading order. The blockquotes are
        no part of the text flow (see class documentation) unless asked for."""
        return [
            leaf
            for leaf in top_level_chapter.leaves_in_reading_order()
            if isinstance(leaf, Paragraph)
            and (blockquotes_included or not isinstance(leaf, BlockQuoteParagraph))
            and leaf.has_page_number(page_number)
        ]

    def _first_paragraph_of_page(
        self, top_level_chapter, page_number: int, blockquotes_included: bool = False
    ) -> Paragraph | None:
        paragraphs = self._paragraphs_of_page(
            top_level_chapter, page_number, blockquotes_included
        )
        return paragraphs[0] if paragraphs else None

    def _last_paragraph_of_page(
        self, top_level_chapter, page_number: int, blockquotes_included: bool = False
    ) -> Paragraph | None:
        paragraphs = self._paragraphs_of_page(
            top_level_chapter, page_number, blockquotes_included
        )
        return paragraphs[-1] if paragraphs else None

    def reconstitute_paragraphs_spreading_over_two_pages(
        self, top_level_chapter
    ) -> None:
        """Merge paragraphs that were split across page boundaries.

        When a page ends with an unfinished Paragraph then the next page begins
        with the end of that Paragraph. In order to reconstitute such Paragraphs
        that were split in two, we need to:
        - find the last Paragraph of a page that is not annotated with the
          "paragraph_fits_on_page" flag
        - the next Paragraph holds the end of the original paragraph
        - merge those two paragraphs into a single Paragraph
        - when doing so make sure that the sentence that got split gets also
          properly reconstituted
        """
        for page_number, next_page_number in self._page_breaks_to_mend(
            top_level_chapter, self._page_requires_paragraph_continuation
        ):
            ill_starting_paragraph = self._first_paragraph_of_page(
                top_level_chapter, next_page_number
            )
            if ill_starting_paragraph is None:
                # Only the search over the whole top level chapter failing is
                # anomalous: sub chapters not holding the page is expected.
                self._diagnostics.warn(
                    f"No paragraph with page number {next_page_number} found "
                    f"(needed to continue the paragraph of page {page_number})."
                )
                continue

            ill_ending_paragraph = self._last_paragraph_of_page(
                top_level_chapter, page_number
            )
            if ill_ending_paragraph is None:
                continue
            if not ill_ending_paragraph.get_sentences():
                continue
            # A table between the two paragraphs interrupts the text flow
            # (e.g. a sentence announcing the table "... align:" is not
            # continued by the paragraph commenting the table).
            if self._table_lies_between(
                top_level_chapter, ill_ending_paragraph, ill_starting_paragraph
            ):
                continue
            # A tail that does not continue the head means there is nothing to
            # continue: not merging is then correct, whatever the hierarchical
            # parents are.
            if not ill_starting_paragraph.get_sentences():
                continue
            if not self._continues(
                ill_ending_paragraph.get_sentences()[-1],
                ill_starting_paragraph.get_sentences()[0],
            ):
                continue
            # The item of a numbered list (e.g. an endnote) starting a page
            # is not the end of the paragraph above, even when the sentence
            # of that paragraph is not recognized as complete (e.g. because
            # it ends with a closing quotation mark).
            if self._heuristic_starts_next_numbered_list_item(
                ill_ending_paragraph, ill_starting_paragraph
            ):
                continue

            self._merge_across_page_break(
                ill_ending_paragraph,
                ill_starting_paragraph,
                page_number,
                next_page_number,
            )

    def _table_lies_between(
        self,
        top_level_chapter,
        ending_paragraph: Paragraph,
        starting_paragraph: Paragraph,
    ) -> bool:
        """Whether a table (or a heading) comes in between two paragraphs (in
        reading order)."""
        ending_paragraph_seen = False
        for leaf in top_level_chapter.leaves_in_reading_order():
            if leaf is starting_paragraph:
                return False
            if leaf is ending_paragraph:
                ending_paragraph_seen = True
            elif ending_paragraph_seen and isinstance(leaf, (Table, Heading)):
                return True
        return False

    def _heuristic_starts_next_numbered_list_item(
        self, ill_ending_paragraph: Paragraph, ill_starting_paragraph: Paragraph
    ) -> bool:
        """Whether the paragraph starting a page is the next item of a numbered list.

        Heuristic, see NumberedListAnnotator. Assumption: a paragraph that
        begins with the number following the last item above is an item, not
        the end of the paragraph cut by the page break. Failure mode: a
        paragraph really cut right before such a number is left unmerged.
        Disable: StructuralInfoBase.numbered_list_heuristics_enabled.
        """
        if not self.structural_info.numbered_list_heuristics_enabled:
            return False
        owner = ill_ending_paragraph._owning_hierarchical_level
        sibling_texts = []
        for sibling in owner.get_sublevels():
            if isinstance(sibling, Paragraph):
                sibling_texts.append(sibling.get_markdown_text())
            if sibling is ill_ending_paragraph:
                break
        return NumberedListAnnotator().heuristic_is_next_item(
            sibling_texts, ill_starting_paragraph.get_markdown_text()
        )

    def _merge_across_page_break(
        self,
        ill_ending_paragraph: Paragraph,
        ill_starting_paragraph: Paragraph,
        page_number: int,
        next_page_number: int,
    ) -> None:
        """Merge the two halves (paragraphs or blockquotes) of an element that
        was cut by a page break, unless they do not share the same parent."""
        # Assert that the page_layout of the two paragraphs do differ
        if ill_ending_paragraph.page_layout == ill_starting_paragraph.page_layout:
            raise ConverterError(
                f"Error: the page layout of the two paragraphs to be merged is the same. This is not expected.\nParagraph ending on page number {page_number} has page layout {repr(ill_ending_paragraph.page_layout)}\nParagraph starting on page number {next_page_number} has page layout {repr(ill_starting_paragraph.page_layout)}"
            )

        last_sentence_of_ill_ending_paragraph = ill_ending_paragraph.get_sentences()[-1]

        # Check parent types match
        if type(ill_starting_paragraph._owning_hierarchical_level) is not type(
            ill_ending_paragraph._owning_hierarchical_level
        ):
            self._diagnostics.warn(
                f"Choosing not to merge the paragraph ending page {ill_ending_paragraph.page_layout.page_number} "
                f"(ends with: {last_sentence_of_ill_ending_paragraph.text[-60:]!r}) and the paragraph starting page "
                f"{ill_starting_paragraph.page_layout.page_number} "
                f"(starts with: {ill_starting_paragraph.get_sentences()[0].text[:60]!r}), because"
            )
            self._diagnostics.warn("their respective parents are of different types: ")
            self._diagnostics.warn(
                f"which are respectively {type(ill_starting_paragraph._owning_hierarchical_level)} and {type(ill_ending_paragraph._owning_hierarchical_level)}."
            )
            return

        # Check same hierarchical parent
        if (
            ill_starting_paragraph._owning_hierarchical_level
            != ill_ending_paragraph._owning_hierarchical_level
        ):
            self._diagnostics.warn(
                f"Choosing not to merge the paragraph ending page {ill_ending_paragraph.page_layout.page_number} "
                f"(ends with: {last_sentence_of_ill_ending_paragraph.text[-60:]!r}) and the paragraph starting page "
                f"{ill_starting_paragraph.page_layout.page_number} "
                f"(starts with: {ill_starting_paragraph.get_sentences()[0].text[:60]!r}), because they are not siblings."
            )
            return

        # Proceed with the merging
        first_sentence_of_ill_starting_paragraph = (
            ill_starting_paragraph.get_sentences()[0]
        )
        # First merge the two sentences:
        last_sentence_of_ill_ending_paragraph.append(
            first_sentence_of_ill_starting_paragraph
        )
        ill_starting_paragraph.remove_sentence(first_sentence_of_ill_starting_paragraph)
        # Then merge the two paragraphs:
        ill_ending_paragraph.merge(ill_starting_paragraph)

    def reconstitute_blockquotes_spreading_over_two_pages(
        self, top_level_chapter
    ) -> None:
        """Merge the blockquotes (pull quotes) that were cut by a page break.

        A blockquote ending a page on an unfinished sentence, immediately
        followed (the pages skipped by the structural info left aside) by a
        blockquote starting the next page, is the two halves of a single
        blockquote. A paragraph starting the next page is running text and is
        never glued to a blockquote. The pages flagged with
        "blockquote_fits_on_page" are left untouched.
        """
        for page_number, next_page_number in self._page_breaks_to_mend(
            top_level_chapter, self._page_requires_blockquote_continuation
        ):
            # Blockquotes included: what ends and starts the pages, whatever
            # its kind, must be blockquotes.
            ending_element = self._last_paragraph_of_page(
                top_level_chapter, page_number, blockquotes_included=True
            )
            if not isinstance(ending_element, BlockQuoteParagraph):
                continue
            starting_element = self._first_paragraph_of_page(
                top_level_chapter, next_page_number, blockquotes_included=True
            )
            if not isinstance(starting_element, BlockQuoteParagraph):
                continue
            if (
                not ending_element.get_sentences()
                or not starting_element.get_sentences()
            ):
                continue
            # A tail that does not continue the head means two distinct
            # blockquotes.
            if not self._continues(
                ending_element.get_sentences()[-1],
                starting_element.get_sentences()[0],
            ):
                continue
            self._merge_across_page_break(
                ending_element, starting_element, page_number, next_page_number
            )

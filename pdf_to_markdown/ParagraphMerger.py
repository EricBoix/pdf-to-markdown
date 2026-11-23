from .Model import (
    TopLevelChapterOfParagraphs,
    SubChapterOfParagraphs,
    BlockQuoteParagraph,
    Paragraph,
    Sentence,
    TopLevelChapter,
)
from .DiagnosticsReporter import DiagnosticsReporter
from .NumberedListAnnotator import NumberedListAnnotator
from .Errors import ConverterError


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
        self._diagnostics = (
            diagnostics if diagnostics is not None else DiagnosticsReporter()
        )

    def _page_requires_paragraph_continuation(self, page_number: int) -> bool:
        if page_number not in self.structural_info.pages_info:
            return True  # Looks a bit ambitious but let's try it
        if "paragraph_fits_on_page" in self.structural_info.pages_info[page_number]:
            return False
        return True

    def _chapter_get_first_paragraph_of_given_page(
        self, chapter, page_number: int
    ) -> Paragraph | None:
        for sublevel in chapter.get_sublevels():
            if isinstance(
                sublevel, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
            ):
                sublevel_result = self._chapter_get_first_paragraph_of_given_page(
                    sublevel, page_number
                )
                if sublevel_result is None:
                    continue
                return sublevel_result
            if isinstance(sublevel, Sentence):
                raise ConverterError("We should have crossed a Paragraph before.")
            if isinstance(sublevel, BlockQuoteParagraph):
                continue  # Not part of the text flow, see class documentation
            if isinstance(sublevel, Paragraph):
                if sublevel.has_page_number(page_number):
                    return sublevel
        return None

    def _chapter_get_last_paragraph_of_given_page(
        self, chapter, page_number: int
    ) -> Paragraph | None:
        sublevel_of_that_page = None
        for sublevel in chapter.get_sublevels():
            if isinstance(
                sublevel, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
            ):
                result = self._chapter_get_last_paragraph_of_given_page(
                    sublevel, page_number
                )
                if result is not None and result.has_page_number(page_number):
                    sublevel_of_that_page = result
                    continue
            if isinstance(sublevel, Sentence):
                raise ConverterError("We should have crossed a Paragraph before.")
            if isinstance(sublevel, BlockQuoteParagraph):
                continue  # Not part of the text flow, see class documentation
            if isinstance(sublevel, Paragraph):
                if sublevel.has_page_number(page_number):
                    sublevel_of_that_page = sublevel
        return sublevel_of_that_page

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
        if not isinstance(top_level_chapter, TopLevelChapter):
            return

        if len(top_level_chapter.pages) == 1:
            return

        for page_index in range(0, len(top_level_chapter.pages) - 1):
            current_page = top_level_chapter.pages[page_index]
            page_number = current_page.page_number
            if not self._page_requires_paragraph_continuation(page_number):
                continue
            next_page_number = (
                self.structural_info._get_page_number_finishing_last_paragraph(
                    page_number
                )
            )
            if self.structural_info._holds_new_chapter(next_page_number):
                continue

            ill_starting_paragraph = self._chapter_get_first_paragraph_of_given_page(
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
            if not isinstance(ill_starting_paragraph, Paragraph):
                self._diagnostics.warn("Ill starting paragraph is not ... a paragraph.")
                self._diagnostics.warn("Not merging.")
                continue

            ill_ending_paragraph = self._chapter_get_last_paragraph_of_given_page(
                top_level_chapter, page_number
            )
            if ill_ending_paragraph is None:
                continue
            if not isinstance(ill_ending_paragraph, Paragraph):
                self._diagnostics.warn("Ill ending paragraph is not ... a paragraph.")
                self._diagnostics.warn("Not merging.")
                continue
            if not ill_ending_paragraph.get_sentences():
                continue
            # A complete last sentence means there is nothing to continue: not
            # merging is then correct, whatever the hierarchical parents are.
            last_sentence_of_ill_ending_paragraph = (
                ill_ending_paragraph.get_sentences()[-1]
            )
            if last_sentence_of_ill_ending_paragraph.is_complete():
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

    def _page_requires_blockquote_continuation(self, page_number: int) -> bool:
        if page_number not in self.structural_info.pages_info:
            return True
        if "blockquote_fits_on_page" in self.structural_info.pages_info[page_number]:
            return False
        return True

    def _chapter_get_first_element_of_given_page(
        self, chapter, page_number: int
    ) -> Paragraph | None:
        """First paragraph or blockquote of the page, whatever its kind."""
        for sublevel in chapter.get_sublevels() or []:
            if isinstance(
                sublevel, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
            ):
                sublevel_result = self._chapter_get_first_element_of_given_page(
                    sublevel, page_number
                )
                if sublevel_result is not None:
                    return sublevel_result
            elif isinstance(sublevel, Paragraph):
                if sublevel.has_page_number(page_number):
                    return sublevel
        return None

    def _chapter_get_last_element_of_given_page(
        self, chapter, page_number: int
    ) -> Paragraph | None:
        """Last paragraph or blockquote of the page, whatever its kind."""
        element_of_that_page = None
        for sublevel in chapter.get_sublevels() or []:
            if isinstance(
                sublevel, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
            ):
                result = self._chapter_get_last_element_of_given_page(
                    sublevel, page_number
                )
                if result is not None:
                    element_of_that_page = result
            elif isinstance(sublevel, Paragraph):
                if sublevel.has_page_number(page_number):
                    element_of_that_page = sublevel
        return element_of_that_page

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
        if not isinstance(top_level_chapter, TopLevelChapter):
            return

        for page_index in range(0, len(top_level_chapter.pages) - 1):
            page_number = top_level_chapter.pages[page_index].page_number
            if not self._page_requires_blockquote_continuation(page_number):
                continue
            next_page_number = (
                self.structural_info._get_page_number_finishing_last_paragraph(
                    page_number
                )
            )
            if self.structural_info._holds_new_chapter(next_page_number):
                continue

            ending_element = self._chapter_get_last_element_of_given_page(
                top_level_chapter, page_number
            )
            if not isinstance(ending_element, BlockQuoteParagraph):
                continue
            starting_element = self._chapter_get_first_element_of_given_page(
                top_level_chapter, next_page_number
            )
            if not isinstance(starting_element, BlockQuoteParagraph):
                continue
            if (
                not ending_element.get_sentences()
                or not starting_element.get_sentences()
            ):
                continue
            # A complete last sentence means two distinct blockquotes.
            if ending_element.get_sentences()[-1].is_complete():
                continue
            self._merge_across_page_break(
                ending_element, starting_element, page_number, next_page_number
            )

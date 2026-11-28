from ..NumberedListAnnotator import NumberedListAnnotator
from .TypoRule import TypoRule


class NumberedItemStartingAPageIsNotAContinuation(TypoRule):
    """The numbering of a document is trustworthy, its layout is not.

    - a paragraph starting a page with the number that follows the last item
      above is the next item, not the end of the paragraph cut by the page
      break;
    - a numbering that restarts at 1 inside an open list is a nested list;
    - a paragraph between two items of a list (at most
      NumberedListAnnotator.MAX_PARAGRAPHS_BETWEEN_ITEMS) belongs to the item
      above.

    Failure mode: a paragraph really cut right before such a number is left
    unmerged, and a paragraph that merely begins with a number is taken for an
    item. The items that belong to no list are the trap: they are kept and
    reported (see NumberedListAnnotator).

    Action sites: ParagraphMerger (the first paragraph of a page) and the
    annotation of the numbered lists of a level (Model, the flag
    numbered_list_heuristics_enabled of the document, set by ConverterBase).
    """

    def starts_next_item(self, preceding_texts: list[str], text: str) -> bool:
        """Whether the text is the item that follows the last item preceding it."""
        return NumberedListAnnotator().heuristic_is_next_item(preceding_texts, text)

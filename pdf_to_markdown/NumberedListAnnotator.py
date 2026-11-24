import logging
import re
from dataclasses import dataclass
from enum import Enum


class NumberedListRole(Enum):
    """The role of a paragraph with respect to the markdown numbered lists."""

    NONE = "none"
    # The paragraph is an item of a numbered list (possibly a nested list).
    ITEM = "item"
    # The paragraph sits between two items of the same numbered list: it must
    # be indented in order to belong to the item it follows (otherwise it
    # breaks the list in several lists, which markdownlint rule MD029 rejects).
    CONTINUATION = "continuation"
    # The paragraph is numbered but fits in no list (broken numbering): the
    # original number is kept and a note is appended for the human reader.
    FAILED = "failed"


@dataclass(frozen=True)
class NumberedListPlacement:
    """The role of a paragraph, and the indentation (number of spaces) it must
    be written with in order to be nested at the right place in its list."""

    role: NumberedListRole = NumberedListRole.NONE
    indentation: int = 0


class NumberedListAnnotator:
    """Detects the numbered lists spread over the paragraphs of a level.

    A pdf document numbers the items of a list ("1. ", "2. ", ...) and
    separates them with paragraphs (continuation of the item, sub-items...).
    Once converted to markdown, each item is a paragraph of its own.

    HEURISTIC. The entry points of this class (their name starts with
    "heuristic_") rest on hypotheses on the text extracted from the pdf, they
    are not deterministic transformations:
    - Assumption: the numbering of the original document is trustworthy (items
      are numbered 1, 2, 3...) but its layout is not: the indentation of a
      nested list may have been lost by the text extraction. A numbering that
      restarts at one while a list is open is thus taken for a nested list, and
      a paragraph between two items of a list is taken for a continuation of
      the item above (when the next item is found within
      MAX_PARAGRAPHS_BETWEEN_ITEMS paragraphs).
    - Failure mode: a wrong hypothesis misindents paragraphs, or makes a list
      out of paragraphs that merely begin with a number. An item that belongs
      to no list is left untouched and reported as a warning (it is a
      deliberate dead end: no attempt is made to repair it), which markdownlint
      rule MD029 then flags in the generated markdown.
    - Disable: StructuralInfoBase.numbered_list_heuristics_enabled (False).
    """

    # Paragraphs separating two consecutive items of a list. Beyond this
    # distance the second numbered paragraph is not taken for the next item.
    MAX_PARAGRAPHS_BETWEEN_ITEMS = 20

    _logger = logging.getLogger("pdf_to_markdown")

    FAILURE_NOTE = "<!-- Converter note: failing on ordered list -->"

    _ITEM_REGEX = re.compile(r"(\d+)\. ")

    def heuristic_annotate(
        self, paragraph_texts: list[str | None]
    ) -> list[NumberedListPlacement]:
        """Return the placement of each paragraph.

        A None text stands for a sibling that is not a paragraph (e.g. a
        sub-chapter): such a sibling ends any list. A numbered paragraph that
        belongs to no list is marked FAILED (and a warning is logged).
        """
        placements = [NumberedListPlacement()] * len(paragraph_texts)
        # The number of the last item of each (nested) open list, outermost
        # list first.
        open_lists: list[int] = []
        for index, text in enumerate(paragraph_texts):
            if text is None:
                open_lists = []
                continue
            item_number = self._item_number(text)
            if item_number is not None:
                depth = self._depth_of_item(open_lists, item_number)
                if depth is None:
                    self._logger.warning(
                        f"Numbered item that belongs to no list, original number kept, note added: {text[:60]!r}"
                    )
                    open_lists = []
                    placements[index] = NumberedListPlacement(NumberedListRole.FAILED)
                    continue
                if depth == len(open_lists):
                    open_lists.append(item_number)
                else:
                    del open_lists[depth + 1 :]
                    open_lists[depth] = item_number
                placements[index] = NumberedListPlacement(
                    NumberedListRole.ITEM, self._indentation(open_lists, depth)
                )
            elif open_lists:
                following_depth = self._depth_of_following_item(
                    paragraph_texts, index, open_lists
                )
                if following_depth is None:
                    open_lists = []
                else:
                    placements[index] = NumberedListPlacement(
                        NumberedListRole.CONTINUATION,
                        self._indentation(open_lists, following_depth + 1),
                    )
        return placements

    @staticmethod
    def _depth_of_item(open_lists: list[int], item_number: int) -> int | None:
        """The depth (0 for the outermost list) of the list an item belongs to.

        None when the item belongs to no list. The depth is len(open_lists)
        for the first item of a nested list.
        """
        for depth in reversed(range(len(open_lists))):
            if item_number == open_lists[depth] + 1:
                return depth
        if item_number == 1:
            return len(open_lists)
        return None

    @staticmethod
    def _indentation(open_lists: list[int], depth: int) -> int:
        """The width of the markers ("12. ") of the lists enclosing a depth."""
        return sum(len(str(number)) + 2 for number in open_lists[:depth])

    def _item_number(self, text: str) -> int | None:
        match = self._ITEM_REGEX.match(text)
        return int(match.group(1)) if match else None

    def _depth_of_following_item(
        self, paragraph_texts: list[str | None], index: int, open_lists: list[int]
    ) -> int | None:
        """The depth of the list of the next item, when it is not too far.

        None when there is no next item, or when it belongs to no open list
        (e.g. it is the "1." of another list).
        """
        last_index = min(
            len(paragraph_texts), index + 1 + self.MAX_PARAGRAPHS_BETWEEN_ITEMS
        )
        for following_text in paragraph_texts[index + 1 : last_index]:
            if following_text is None:
                return None
            following_number = self._item_number(following_text)
            if following_number is not None:
                # Any item ends the search. A "1." is not taken for a nested
                # list here, since the text in between would then belong to
                # the list (e.g. two lists separated by prose).
                for depth in reversed(range(len(open_lists))):
                    if following_number == open_lists[depth] + 1:
                        return depth
                return None
        return None

    def heuristic_is_next_item(self, preceding_texts: list[str], text: str) -> bool:
        """Whether the text is the item following the last item preceding it.

        Heuristic, see the class documentation: the numbering is trusted.

        The last item among the preceding paragraphs is looked for no further
        than MAX_PARAGRAPHS_BETWEEN_ITEMS paragraphs away.
        """
        item_number = self._item_number(text)
        if item_number is None:
            return False
        for preceding_text in reversed(
            preceding_texts[-(self.MAX_PARAGRAPHS_BETWEEN_ITEMS + 1) :]
        ):
            preceding_number = self._item_number(preceding_text)
            if preceding_number is not None:
                return item_number == preceding_number + 1
        return False

    @staticmethod
    def indent(text: str, indentation: int) -> str:
        """Indent the text so it belongs to the numbered list item above."""
        return " " * indentation + text

    @classmethod
    def annotate_failure(cls, text: str) -> str:
        """Append the converter note to an item that fits in no list."""
        return text + cls.failure_suffix()

    @classmethod
    def failure_suffix(cls) -> str:
        """What annotate_failure appends to the text."""
        return f" {cls.FAILURE_NOTE}"

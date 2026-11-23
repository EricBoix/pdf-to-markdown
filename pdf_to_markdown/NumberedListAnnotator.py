import re
from enum import Enum


class NumberedListRole(Enum):
    """The role of a paragraph with respect to the markdown numbered lists."""

    NONE = "none"
    # The paragraph sits between two items of the same numbered list: it must
    # be indented in order to belong to the item it follows (otherwise it
    # breaks the list in several lists, which markdownlint rule MD029 rejects).
    CONTINUATION = "continuation"
    # The paragraph looks like an item of a list that was never started
    # (e.g. it begins with "2. " but no "1. " precedes it): its dot is escaped
    # so that markdown does not take it for the start of a list that does not
    # begin at one.
    ESCAPED_ITEM = "escaped_item"


class NumberedListAnnotator:
    """Detects the numbered lists spread over the paragraphs of a level.

    A pdf document numbers the items of a list ("1. ", "2. ", ...) and
    separates them with paragraphs (continuation of the item, sub-items...).
    Once converted to markdown, each item is a paragraph of its own: the lists
    must be told apart from the paragraphs holding a number by accident.
    """

    # Paragraphs separating two consecutive items of a list. Beyond this
    # distance the second numbered paragraph is not taken for the next item.
    MAX_PARAGRAPHS_BETWEEN_ITEMS = 20

    _ITEM_REGEX = re.compile(r"(\d+)\. ")

    def annotate(self, paragraph_texts: list[str | None]) -> list[NumberedListRole]:
        """Return the role of each paragraph.

        A None text stands for a sibling that is not a paragraph (e.g. a
        sub-chapter): such a sibling ends any list.
        """
        roles = [NumberedListRole.NONE] * len(paragraph_texts)
        open_item_number = None
        for index, text in enumerate(paragraph_texts):
            if text is None:
                open_item_number = None
                continue
            item_number = self._item_number(text)
            if item_number is not None:
                if item_number == 1 or item_number == self._next(open_item_number):
                    open_item_number = item_number
                else:
                    roles[index] = NumberedListRole.ESCAPED_ITEM
                    open_item_number = None
            elif open_item_number is not None:
                if self._next_item_follows(
                    paragraph_texts, index, open_item_number + 1
                ):
                    roles[index] = NumberedListRole.CONTINUATION
                else:
                    open_item_number = None
        return roles

    @staticmethod
    def _next(item_number: int | None) -> int | None:
        return None if item_number is None else item_number + 1

    def _item_number(self, text: str) -> int | None:
        match = self._ITEM_REGEX.match(text)
        return int(match.group(1)) if match else None

    def _next_item_follows(
        self, paragraph_texts: list[str | None], index: int, wanted_number: int
    ) -> bool:
        last_index = min(
            len(paragraph_texts), index + 1 + self.MAX_PARAGRAPHS_BETWEEN_ITEMS
        )
        for following_text in paragraph_texts[index + 1 : last_index]:
            if following_text is None:
                return False
            if self._item_number(following_text) == wanted_number:
                return True
        return False

    @staticmethod
    def escape_item(text: str) -> str:
        """Escape the dot of the item number heading the text."""
        return re.sub(r"^(\d+)\.", r"\1\\.", text)

    @staticmethod
    def indent_continuation(text: str) -> str:
        """Indent the text so it belongs to the numbered list item above."""
        return "   " + text

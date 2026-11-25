from dataclasses import dataclass
from enum import Enum


class PartKind(Enum):
    """What a part of the text of a level of paragraphs is."""

    PARAGRAPH = "paragraph"
    BLOCKQUOTE = "blockquote"
    # The text of such a part is the name of the table, as found in the
    # TablePlaceholder that the TableExtractor left in the text of the page.
    TABLE = "table"
    # The title of a sub-section that the hierarchy of levels has no level for.
    HEADING = "heading"


@dataclass(frozen=True)
class Part:
    """A part of the text of a level of paragraphs, as cut out by a splitter
    (see ParagraphAndBlockquoteSplitter): its kind, and its text."""

    kind: PartKind
    text: str

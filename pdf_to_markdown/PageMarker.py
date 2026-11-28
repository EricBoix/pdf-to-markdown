import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

from .PageLayout import PageLayout


@dataclass(frozen=True)
class PageMarker:
    """The page that the text following it in the markdown comes from.

    It is written as an html comment, e.g.

        <!-- page reader=iv pdf=4 -->

    - reader is the page number printed on the page: an integer, or whatever
      the book prints (e.g. "Cover", or a roman numeral for the preamble). It
      is percent encoded, so that any text is safe within the comment.
    - pdf is the page as a PDF viewer numbers it: the first page is 1 (the
      page_number of a PageLayout is the index of the page, which starts at 0).

    A marker stands before the first sentence that is on its page: a sentence
    that a page break cuts belongs to the page where it starts. Within a
    paragraph the marker is written on a line of its own, the paragraph text
    resuming on the next line (a single newline before and after: no blank line,
    hence no new paragraph in the source markdown: the chapter / paragraph /
    sentence numbering is unchanged). The markers come from the page breaks of
    the document (see PageBreak).
    """

    reader_page_number: int | str
    pdf_page_number: int

    PATTERN = re.compile(r"<!-- page reader=(?P<reader>\S+) pdf=(?P<pdf>\d+) -->")

    @classmethod
    def from_layout(cls, layout: PageLayout) -> "PageMarker":
        return cls(layout.reader_page_number, layout.page_number + 1)

    @classmethod
    def from_match(cls, match: re.Match) -> "PageMarker":
        reader = unquote(match.group("reader"))
        return cls(int(reader) if reader.isdigit() else reader, int(match.group("pdf")))

    @classmethod
    def parse(cls, text: str) -> "PageMarker | None":
        """The marker that a comment is, None when it is not a page marker."""
        match = cls.PATTERN.fullmatch(text.strip())
        return cls.from_match(match) if match else None

    def to_comment(self) -> str:
        reader = quote(str(self.reader_page_number), safe="")
        return f"<!-- page reader={reader} pdf={self.pdf_page_number} -->"

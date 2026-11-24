from abc import ABC
from typing import Generic, TypeVar
import re
import nltk
from mdutils.mdutils import MdUtils

# Ensure NLTK data is available (downloads once if missing)
for resource, path in [
    ("punkt_tab", "tokenizers/punkt_tab"),
    ("averaged_perceptron_tagger_eng", "taggers/averaged_perceptron_tagger_eng"),
]:
    try:
        nltk.data.find(path)
    except LookupError:
        nltk.download(resource, quiet=True)
import logging

from .Errors import ConverterError
from .NumberedListAnnotator import (
    NumberedListAnnotator,
    NumberedListPlacement,
    NumberedListRole,
)
from .LineWrapper import LineWrapper
from .PageLayout import PageLayout
from .TableRegistry import SpanningCellText

# Type variable for sublevel types in DocumentHierarchicalLevel
T = TypeVar("T", bound="DocumentHierarchicalLevel | None")


class Numbered:
    def __init__(self) -> None:
        # Numbering of this hierarchical level is the position within the
        # container of the owning hierarchical level. Note that this numbering
        # is for human consumption and thus starts at 1, not 0.
        self._number: int | None = None

    @property
    def number(self) -> int | None:
        return self._number

    def set_number(self, number: int) -> None:
        self._number = number


class Parent:
    """Reference to a higher level within a hierarchy."""

    def __init__(self) -> None:
        self._owning_hierarchical_level = None

    def set_owning_hierarchical_level(self, parent) -> None:
        self._owning_hierarchical_level = parent

    @property
    def owning_hierarchical_level(self) -> "DocumentHierarchicalLevel | None":
        return self._owning_hierarchical_level

    @property
    def hierarchical_toplevel(self) -> "DocumentHierarchicalLevel | None":
        level = self
        while level.owning_hierarchical_level:
            level = level.owning_hierarchical_level
        return level


class Sentence(Numbered, Parent):
    """
    A sentence _has_ a Layout (a page identifier for the reader to retrieve it)
    """

    def __init__(self, text: str, layout: PageLayout) -> None:
        self.text = text
        self.page_layout = layout.__copy__()

    def append(self, other: "Sentence") -> None:
        """
        Append text to the current sentence.
        """
        self.text += " " + other.text

    def is_complete(self) -> bool:
        # The problem is hard, refer e.g. to
        # https://stackoverflow.com/questions/71590785/nlp-check-if-a-detected-sentence-is-a-complete-sentence
        # We check:
        # - starts with a capital letter
        # - ends with punctuation
        # - contains a verb (using NLTK POS tagging)
        if not self.text[0].isupper():
            return False
        if not bool(re.search(r"[.!?]$", self.text)):
            return False
        tokens = nltk.word_tokenize(self.text)
        tagged = nltk.pos_tag(tokens)
        has_verb = any(tag.startswith("VB") for _, tag in tagged)
        return has_verb

    def to_markdown(self, md_file: MdUtils, dummy_level) -> None:
        """
        Add this sentence's content to the given MdUtils object.
        """
        md_file.new_line(repr(self.text))

    def get_document_reference_long(self) -> str:
        # Paragraphs are nameless so we must grab the grand-parent
        owner_name = (
            self.owning_hierarchical_level.owning_hierarchical_level.name
            if self.owning_hierarchical_level
            else "unknown"
        )
        paragraph_number = (
            self.owning_hierarchical_level.number
            if self.owning_hierarchical_level
            else "unknown"
        )
        page_reader = self.page_layout.reader_page_number if self.page_layout else "?"

        return f"Source document: {self.hierarchical_toplevel.get_title()}, Chapter: {owner_name}, paragraph number {paragraph_number}, sentence number {self._number} on page {page_reader}"


class DocumentHierarchicalLevel(ABC, Generic[T], Numbered, Parent):
    """
    A chapter, a sub-chapter, a sub-sub-chapter, with an optional list of sublevels.
    The type parameter T specifies the allowed sublevel type.
    """

    # Trailing punctuation characters that markdownlint rule MD026 rejects in
    # a header (the rule's default set, which notably excludes '?').
    HEADER_TRAILING_PUNCTUATION = ".,;:!。，；：！"
    MARKDOWNLINT_DISABLE_MD026 = "<!-- markdownlint-disable-line MD026 -->"

    _logger = logging.getLogger("pdf_to_markdown")

    def __init__(self, name: str) -> None:
        Numbered.__init__(self)
        Parent.__init__(self)
        self.name: str = name
        if not self.name:
            self._logger.warning(
                "DocumentHierarchicalLevel created with no given name."
            )
        # The text capturing this level as extracted from the original document.
        # Note that this text is only used in order to construct this model
        # during the hierarchical breakdown. Eventually all the text content
        # will end up (copied) in the Sentence (leaves of the hierarchy) or
        # intermediate level titles (e.g. chapter title)
        self.text: str = None
        # The optional sub-hierarchical levels of this one
        self.sublevels: list[T] | None = None
        # The page where this Hierarchical level is encountered within the
        # original document
        self.page_layout: PageLayout | None = None

    def get_text_with_layout(self) -> list:
        # Used to get some (artificial) genericity with DocumentHierarchicalRoot
        # where the original document text is stored in pages that have both
        # a text and a layout_page attribute.
        return [self]

    def add_sublevel(self, sublevel: T) -> None:
        if not self.sublevels:
            self.sublevels = list()
        self.sublevels.append(sublevel)
        sublevel.set_owning_hierarchical_level(self)

    def get_sublevel(self, index: int) -> T:
        if not self.sublevels or index >= len(self.sublevels):
            raise ConverterError(
                f"Sublevel index {index} out of bounds: should be smaller than {len(self.sublevels) if self.sublevels else 0}"
            )
        return self.sublevels[index]

    def get_last_sublevel(self) -> T | None:
        if not self.sublevels:
            self._logger.warning("No sublevels found.")
            return None
        return self.sublevels[-1]

    def remove_sublevel(self, sublevel: T) -> None:
        """
        Remove a sublevel from this hierarchical level.
        """
        if self.sublevels and sublevel in self.sublevels:
            self.sublevels.remove(sublevel)
        else:
            raise ValueError("Sublevel not found.")

    def get_sublevels(self) -> list[T] | None:
        return self.sublevels

    def set_name(self, name: str) -> None:
        self.name = name

    def append_text(self, text: str) -> None:
        if self.text:
            self.text += text
        else:
            self.text = text

    def renumber_sublevels(self) -> None:
        if self.sublevels:
            for index, sublevel in enumerate(self.sublevels, start=1):
                sublevel.set_number(index)

    def has_page_number(self, page_number) -> bool:
        return self.page_layout.page_number == page_number

    def get_first_sublevel_of_given_page(self, page_number) -> T | None:
        for sublevel in self.sublevels:
            if sublevel.page_layout.page_number == page_number:
                return sublevel
        self._logger.warning(
            f"unable to find the first sublevel of page number {page_number} in hierarchy {self.name}"
        )
        return None

    def get_last_sublevel_of_given_page(self, page_number) -> T | None:
        sublevel_of_that_page = None
        for sublevel in self.sublevels:
            if sublevel.page_layout.page_number == page_number:
                sublevel_of_that_page = sublevel
        if sublevel_of_that_page is None:
            self._logger.warning(
                f"unable to find the last sublevel of page number {page_number} in hierarchy {self.name}"
            )
        return sublevel_of_that_page

    def merge(self, other: "DocumentHierarchicalLevel") -> None:
        """
        Concatenate another DocumentHierarchicalLevel to this one and dispose
        of the other. This method assumes that this instance and the other DocumentHierarchicalLevel both share the same hierarchical parent.
        """
        if type(self) is not type(other):
            raise ConverterError("Cannot merge two different types.")
        if self.owning_hierarchical_level != other.owning_hierarchical_level:
            if type(self.owning_hierarchical_level) is not type(
                other.owning_hierarchical_level
            ):
                # We should inquire further but we are probably in the case
                # where:
                #  - self and other are both paragraphs
                #  - type(parent(self)) is a SuperChapter
                #  - type(parent(other)) is a ChapterOfParagraph (that belongs
                #    to the same SuperChapter)
                # Although the paragraphs follow themselves, they do not share
                # the same parent (but the same grand-parent).
                self._logger.warning(
                    f"Choosing not to merge {self} and {other}, because"
                )
                self._logger.warning(
                    f"their respective parent are of different types, that"
                )
                self._logger.warning(
                    f"are {type(self.owning_hierarchical_level)} and {type(other.owning_hierarchical_level)}."
                )
                return
            else:
                self._logger.warning(
                    f"Choosing not to merge {self} from page {self.page_layout.page_number} and {other} from page {other.page_layout.page_number}, because they are not siblings."
                )
                return
        if self.owning_hierarchical_level is None:
            raise ConverterError(
                "DocumentHierarchicalLevel has no owning hierarchical level."
            )
        self.sublevels.extend(other.sublevels)
        self.owning_hierarchical_level.remove_sublevel(other)
        self.owning_hierarchical_level.renumber_sublevels()

    def to_markdown(self, md_file: MdUtils, level) -> None:
        """
        Add this hierarchical level's content to the given MdUtils object.
        """
        if not self.name:
            raise ConverterError("No name for markdown conversion.")
        # MdUtils.new_header() ends with a newline and MdUtils.new_paragraph()
        # starts with two newlines: a header followed by a paragraph would thus
        # get two blank lines instead of one. Hence we write the (atx) header
        # ourselves, without its trailing newline.
        header = "#" * level + " " + self.name
        if self.name.endswith(tuple(self.HEADER_TRAILING_PUNCTUATION)):
            # The punctuation legitimately comes from the original document:
            # silence markdownlint (MD026) for this very line only.
            header += self.MARKDOWNLINT_DISABLE_MD026
        # markdownlint rule MD022 requires a blank line before a header, that
        # is two newlines. What precedes depends on the previous sibling: a
        # paragraph does not end with a newline (MdUtils.new_paragraph()
        # starts with two newlines, but does not end with any) whereas a
        # level ends with a newline.
        previous_text = md_file.file_data_text
        trailing_newlines = len(previous_text) - len(previous_text.rstrip("\n"))
        missing_newlines = 1 if not previous_text else max(0, 2 - trailing_newlines)
        md_file.write("\n" * missing_newlines + header)
        if self.sublevels and not isinstance(self.sublevels[0], (Paragraph, Table)):
            # A sub header (unlike a paragraph) does not start with a blank
            # line of its own: provide the blank line separating the headers.
            md_file.write("\n")
        if self.sublevels:
            self._heuristic_annotate_numbered_lists()
            for sublevel in self.sublevels:
                if sublevel is not None:
                    sublevel.to_markdown(md_file, level + 1)
        md_file.new_line()

    def _heuristic_annotate_numbered_lists(self) -> None:
        """Tell each paragraph its place in the numbered lists of this level.

        Heuristic, see NumberedListAnnotator. Nothing is done when the
        document has the numbered list heuristics disabled.
        """
        if not getattr(
            self.hierarchical_toplevel, "numbered_list_heuristics_enabled", True
        ):
            return
        paragraph_texts = [
            sublevel.get_markdown_text() if isinstance(sublevel, Paragraph) else None
            for sublevel in self.sublevels
        ]
        placements = NumberedListAnnotator().heuristic_annotate(paragraph_texts)
        for sublevel, placement in zip(self.sublevels, placements):
            if isinstance(sublevel, Paragraph):
                sublevel.numbered_list_placement = placement


class Paragraph(DocumentHierarchicalLevel[Sentence]):
    """
    A list of sentences. Lowest level in the document hierarchy.
    Sentence is a leaf and not a DocumentHierarchicalLevel.
    """

    def __init__(self, layout: PageLayout) -> None:
        """A paragraph is a set of sentences"""
        DocumentHierarchicalLevel.__init__(self, name="Paragraph")
        self.page_layout = layout
        # Set by the owning level when converting to markdown
        self.numbered_list_placement = NumberedListPlacement()

    remove_sentence = DocumentHierarchicalLevel.remove_sublevel
    get_sentences = DocumentHierarchicalLevel.get_sublevels

    def get_document_reference_long(self) -> str:
        # A reference within the document for human consumption.
        owner_name = (
            self.owning_hierarchical_level.name
            if self.owning_hierarchical_level
            else "unknown"
        )
        page_reader = self.page_layout.reader_page_number if self.page_layout else "?"
        page_num = self.page_layout.page_number if self.page_layout else "?"
        return (
            "Paragraph "
            + str(self._number)
            + " of subchapter "
            # Just to add parentheses
            + repr(owner_name)
            + ", page "
            + str(page_reader)
            + " (index page number "
            + str(page_num)
            + ")"
        )

    def to_markdown(self, md_file: MdUtils, dummy_level) -> None:
        """
        Add this paragraph's content to the given MdUtils object.
        Overrides base class to output sentences instead of sublevels.
        """
        sentences = self.get_sublevels()
        if not sentences:
            self._logger.warning("Useless paragraph with no sentences.")
            self._logger.warning("Optimisation inquiry required.")
            return
        # Note: we can not delegate the markdown generation to
        # Sentence.to_markdown() since we would have to use md_file.new_line()
        # which (as expected) adds an unwanted mandatory line break
        md_file.new_paragraph(self._get_markdown_lines())

    def get_markdown_text(self) -> str:
        """The text of the paragraph, as written in markdown (no list role)."""
        return " ".join([sentence.text for sentence in self.get_sublevels()])

    # What every line of the paragraph starts with (e.g. "> " of a blockquote)
    LINE_MARKER = ""

    def _get_markdown_lines(self) -> str:
        """The paragraph as emitted: list role applied, then lines broken.

        The lines are broken last, once the numbered list role is known (it
        provides the indentation of the lines and an optional trailing note),
        at the end of sentences when possible (see LineWrapper). Lines are
        only separated by a single newline: no new paragraph is introduced.
        """
        placement = self.numbered_list_placement
        failed = placement.role == NumberedListRole.FAILED
        line_prefix = ("" if failed else " " * placement.indentation) + self.LINE_MARKER
        return LineWrapper.wrap_sentences(
            [sentence.text for sentence in self.get_sublevels()],
            getattr(self.hierarchical_toplevel, "maximum_line_length", None),
            line_prefix,
            suffix=NumberedListAnnotator.failure_suffix() if failed else "",
        )


class BlockQuoteParagraph(Paragraph):
    """A paragraph that originated from a markdown blockquote (> …).

    It may also originate from a pdf document, as a block set apart from the
    running text (e.g. a pull quote). Such a block is detected by the
    ParagraphAndBlockquoteSplitter of the book's structural info.
    """

    # Each broken line must start with the blockquote marker (parsers that
    # work line by line do not know about "lazy continuation lines").
    LINE_MARKER = "> "

    def __init__(self, layout: PageLayout) -> None:
        Paragraph.__init__(self, layout)

    def to_markdown(self, md_file: MdUtils, dummy_level) -> None:
        sentences = self.get_sublevels()
        if not sentences:
            self._logger.warning("Useless blockquote paragraph with no sentences.")
            return
        md_file.new_paragraph(self._get_markdown_lines())

    def get_markdown_text(self) -> str:
        return "> " + Paragraph.get_markdown_text(self)


class Table(Numbered, Parent):
    """A table of the original document, a leaf of the hierarchy (like a Sentence).

    Its cells are text: it is not broken into sentences. A table is cut out of
    the pages by the TableExtractor, following the declarations of the book's
    structural info.
    """

    # Markdown has no colspan: the cells that a spanning row leaves aside (and
    # the cells of the header row that the caption does not use) are filled
    # with this horizontal line.
    SEPARATOR_FILLER = "────────────────"

    _logger = logging.getLogger("pdf_to_markdown")

    def __init__(
        self,
        layout: PageLayout,
        name: str,
        caption: str | None,
        has_column_headings: bool,
        rows: list[list[str]],
    ) -> None:
        Numbered.__init__(self)
        Parent.__init__(self)
        self.name = name
        self.caption = caption
        self.has_column_headings = has_column_headings
        # A row is a list of cell texts. When the table has column headings
        # the first row is the one of the headings.
        self.rows = rows
        self.page_layout = layout
        # A table has no text of its own, refer to Paragraph.text.
        self.text = None

    def get_sentences(self) -> None:
        """A table has no sentences (this is for the callers walking paragraphs)."""
        return None

    def get_document_reference_long(self) -> str:
        page_reader = self.page_layout.reader_page_number if self.page_layout else "?"
        return f"Table {self.name!r} (page {page_reader})"

    def to_markdown(self, md_file: MdUtils, dummy_level) -> None:
        """Add this table to the given MdUtils object."""
        if not self.rows:
            self._logger.warning(f"Useless table {self.name!r} with no rows.")
            return
        if self.has_column_headings and self.caption:
            # A line above the table (not emphasized, which would trigger the
            # markdownlint rule MD036).
            md_file.new_paragraph(self.caption)
        md_file.new_paragraph("\n".join(self.get_markdown_lines()))

    def get_markdown_lines(self) -> list[str]:
        column_count = max(len(row) for row in self.rows)
        if self.has_column_headings:
            header_row = self.rows[0]
            body_rows = self.rows[1:]
        else:
            # Markdown requires a header row: the caption takes that place.
            header_row = [self.caption or ""] + [self.SEPARATOR_FILLER] * (
                column_count - 1
            )
            body_rows = self.rows
        delimiter_row = ["---"] * column_count
        return [
            self._row_to_markdown(row, column_count)
            for row in [header_row, delimiter_row] + body_rows
        ]

    @classmethod
    def _row_to_markdown(cls, row: list[str], column_count: int) -> str:
        if row and isinstance(row[0], SpanningCellText):
            # A row spanning all the columns: markdown has no colspan, see
            # SEPARATOR_FILLER.
            row = ["**" + row[0] + "**"] + [cls.SEPARATOR_FILLER] * (column_count - 1)
        padded_row = row + [""] * (column_count - len(row))
        # An empty cell is a single whitespace between its pipes (markdownlint
        # rule MD060, compact style).
        formatted_cells = [
            " " + cell.replace("|", "\\|") + " " if cell else " " for cell in padded_row
        ]
        return "|" + "|".join(formatted_cells) + "|"


class TopLevelChapter:
    def __init__(self) -> None:
        # The original pages of the document constituting this chapter
        self.pages: list[str] = list()

    def add_page(self, page) -> None:
        if not self.pages:
            self.page_layout = page.page_layout
        self.pages.append(page)

    def get_text_with_layout(self) -> list:
        return self.pages


class TopLevelChapterOfParagraphs(
    TopLevelChapter, DocumentHierarchicalLevel[Paragraph]
):
    """Chapter with pages, used as direct children of Document."""

    def __init__(self, name: str) -> None:
        DocumentHierarchicalLevel.__init__(self, name)
        TopLevelChapter.__init__(self)

    def get_text_with_layout(self) -> list:
        return self.pages

    def get_document_reference_long(self) -> str:
        """A reference within the document for human consumption."""
        owner_name = (
            self.owning_hierarchical_level.name
            if self.owning_hierarchical_level
            else "unknown"
        )
        page_reader = self.page_layout.reader_page_number if self.page_layout else "?"
        page_num = self.page_layout.page_number if self.page_layout else "?"
        return (
            "Chapter "
            + str(self._number)
            + repr(owner_name)
            + ", page "
            + str(page_reader)
            + " (index page number "
            + str(page_num)
            + ")"
        )


class SubChapterOfParagraphs(DocumentHierarchicalLevel[Paragraph]):
    """Sub-chapter with text, used as children of SuperChapter."""

    def __init__(self, name: str) -> None:
        DocumentHierarchicalLevel.__init__(self, name)

    def get_text_with_layout(self) -> list:
        return [self]

    def get_document_reference_long(self) -> str:
        """A reference within the document for human consumption."""
        owner_name = (
            self.owning_hierarchical_level.name
            if self.owning_hierarchical_level
            else "unknown"
        )
        page_reader = self.page_layout.reader_page_number if self.page_layout else "?"
        page_num = self.page_layout.page_number if self.page_layout else "?"
        return (
            "SubChapter "
            + str(self._number)
            + repr(owner_name)
            + ", page "
            + str(page_reader)
            + " (index page number "
            + str(page_num)
            + ")"
        )


class SuperChapter(TopLevelChapter, DocumentHierarchicalLevel[SubChapterOfParagraphs]):
    def __init__(self, name: str) -> None:
        DocumentHierarchicalLevel.__init__(self, name)
        TopLevelChapter.__init__(self)

    add_chapter = DocumentHierarchicalLevel.add_sublevel
    remove_chapter = DocumentHierarchicalLevel.remove_sublevel
    get_chapters = DocumentHierarchicalLevel.get_sublevels
    renumber_chapters = DocumentHierarchicalLevel.renumber_sublevels

    def is_SuperChapterOfParagraph(self) -> bool:
        if not self.get_sublevels():
            # We can not really decide.
            return False
        some_sublevel = self.get_last_sublevel()
        if isinstance(some_sublevel, Paragraph):
            return True
        return False


class PublicationInfo:
    """Publication metadata supplied by the doc-steward, separate from parsing rules."""

    def __init__(
        self, doc_name: str, author: str | None = None, isbn: str | None = None
    ) -> None:
        self.doc_name = doc_name
        self.author = author
        self.isbn = isbn


class DocumentHierarchicalRoot:
    """
    A list of Chapters.
    """

    _logger = logging.getLogger("pdf_to_markdown")

    def __init__(
        self, title, publication_info: "PublicationInfo | None" = None
    ) -> None:
        self.title = title
        self.publication_info = publication_info
        # See NumberedListAnnotator (set from the structural information)
        self.numbered_list_heuristics_enabled = True
        # See LineWrapper (None: the lines of the paragraphs are never broken)
        self.maximum_line_length = None

    def get_title(self) -> str:
        return self.title

    def get_chapter_name(self, page_number):
        chapter = self.get_first_sublevel_of_given_page(page_number)
        if chapter:
            return chapter.name
        self._logger.warning(f"chapter with page number {page_number} not found.")
        return None

    def to_markdown(self, filepath: str) -> None:
        """
        Generate a markdown file representing the document.
        """
        md_file = MdUtils(
            file_name=filepath, title=self.title, title_header_style="atx"
        )
        for chapter in self.get_chapters():
            chapter.to_markdown(md_file, level=2)
        # Appending a "table a content" makes the Markdown to Pdf conversion
        # fail. This is because (well inquire on that) converting the table of
        # contents requires converting markdown links (things of the form
        # "[some name](#some-name-tag)") and resolving them, when they
        # do not exist in the text:
        #    md_file.new_table_of_contents(table_title="Contents", depth=2)
        md_file.create_md_file()


class Document(
    DocumentHierarchicalRoot, DocumentHierarchicalLevel[TopLevelChapterOfParagraphs]
):
    def __init__(
        self, title: str, publication_info: "PublicationInfo | None" = None
    ) -> None:
        DocumentHierarchicalRoot.__init__(self, title, publication_info)
        DocumentHierarchicalLevel.__init__(self, "Document")

    add_chapter = DocumentHierarchicalLevel.add_sublevel
    get_chapters = DocumentHierarchicalLevel.get_sublevels


class DocumentWithSubChapters(
    DocumentHierarchicalRoot, DocumentHierarchicalLevel[SuperChapter]
):
    def __init__(
        self, title: str, publication_info: "PublicationInfo | None" = None
    ) -> None:
        DocumentHierarchicalRoot.__init__(self, title, publication_info)
        DocumentHierarchicalLevel.__init__(self, "DocumentWithSubChapters")

    add_chapter = DocumentHierarchicalLevel.add_sublevel
    get_chapters = DocumentHierarchicalLevel.get_sublevels

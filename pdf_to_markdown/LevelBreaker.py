from dataclasses import dataclass
from typing import Callable, Protocol

from .Model import (
    BlockQuoteParagraph,
    DocumentHierarchicalLevel,
    SubChapterOfParagraphs,
    Paragraph,
    Table,
    Heading,
)
from .PageLayout import PageLayout
from .Part import Part, PartKind
from .TableRegistry import TableRegistry
from .TextSanitizer import TextSanitizer
from .DiagnosticsReporter import DiagnosticsReporter
from .Errors import ConverterError


class Splitter(Protocol):
    """Protocol for level splitters.

    What split() returns depends on the level that is split:
    - the splitter of a level of sub-chapters returns the text cut around the
      names of the sub-chapters, as a list of str: the text standing before the
      first name if any, then alternately the text holding a name and the text
      of that sub-chapter;
    - the splitter of a level of paragraphs returns a list of Parts (see
      ParagraphAndBlockquoteSplitter).
    """

    def split(self, content_text: str) -> list[str] | list[Part]: ...
    def get_sublevel_name(self, content_text: str) -> str | None: ...


class ContentWithLayout(Protocol):
    """Protocol for content with page layout."""

    text: str
    page_layout: PageLayout


@dataclass
class TextWithLayout:
    """Some text and the layout (the page) it comes from."""

    text: str
    page_layout: PageLayout


class LevelBreaker:
    """
    Breaks a DocumentHierarchicalLevel into sublevels using a splitter.
    Extracted from ConverterBase to simplify the code structure.
    """

    def __init__(
        self,
        level: DocumentHierarchicalLevel,
        level_splitter: Splitter,
        sublevel_factory: Callable[[PageLayout | None], DocumentHierarchicalLevel],
        break_level_callback: Callable[[DocumentHierarchicalLevel], None],
        break_paragraphs_callback: Callable[
            [DocumentHierarchicalLevel, list[ContentWithLayout] | None], None
        ],
        diagnostics: DiagnosticsReporter | None = None,
        table_registry: TableRegistry | None = None,
    ) -> None:
        self.level = level
        self.level_splitter = level_splitter
        self.sublevel_factory = sublevel_factory
        self.break_level = break_level_callback
        self.break_paragraphs = break_paragraphs_callback
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)
        self._table_registry = table_registry

    def break_into_sublevels(
        self, contents: list[ContentWithLayout] | None = None
    ) -> None:
        """Break a hierarchical level into sublevels using the provided splitter."""
        self._diagnostics.debug(
            f"########### break_into_sublevels, level: {self.level}"
        )

        if not contents:
            contents = self.level.get_text_with_layout()
            if not contents:
                self._diagnostics.warn(
                    f"DocumentHierarchicalLevel {self.level} with NO text content."
                )

        current_level = self.level
        # A sublevel name (e.g. a section title) may be the very last line of
        # the text of a content (page) while the text it names starts on the
        # next content. Such a name is then carried over, and prepended to the
        # text of the next content, in order to be broken like any other name.
        pending_name_text = ""
        # The page the carried over name is printed on (a name belongs to the
        # page where it is printed, whereas the text it names starts on the next
        # one, see HeadingIsOnItsPrintedPage).
        pending_name_layout: PageLayout | None = None
        for level_content in contents:
            content_text = level_content.text or ""
            name_layout = pending_name_layout
            if pending_name_text and content_text:
                # The newline is the one that ended the name on its page.
                content_text = pending_name_text + "\n" + content_text
            else:
                name_layout = None
            pending_name_text = ""
            pending_name_layout = None
            self._diagnostics.debug(
                f"####### break_into_sublevels, contents: {content_text}"
            )
            if not content_text:
                self._diagnostics.warn(f"level with NO text.")
                continue

            content_layout = level_content.page_layout
            new_layout = content_layout.__copy__()

            parts = self.level_splitter.split(content_text)
            while parts:
                self._diagnostics.debug(
                    f"### break_into_sublevels, ({len(parts)}) parts: {parts}"
                )

                if self._is_trailing_name_only(parts, level_content is contents[-1]):
                    pending_name_text = parts[0]
                    pending_name_layout = name_layout or new_layout
                    break

                new_sublevel, parts = self._try_create_sublevel(new_layout, parts)
                if new_sublevel:
                    if name_layout is not None:
                        # The text of the sub-level was broken with the page it is
                        # printed on (_try_create_sublevel), the sub-level itself
                        # is on the page of its name.
                        new_sublevel.page_layout = name_layout.__copy__()
                    name_layout = None
                    current_level = new_sublevel
                    continue
                name_layout = None

                should_break, parts = self._handle_unbreakable_text(
                    new_layout, current_level, parts
                )
                if should_break:
                    break

    def _is_trailing_name_only(self, parts: list[str], is_last_content: bool) -> bool:
        """Whether the remaining parts boil down to a sublevel name that has no
        text yet, and that thus has to be carried over to the next content."""
        if is_last_content or len(parts) != 1:
            return False
        if type(self.sublevel_factory(None)) == Paragraph:
            return False
        return bool(self.level_splitter.get_sublevel_name(parts[0]))

    def _try_create_sublevel(
        self, new_layout: PageLayout, parts: list[str]
    ) -> tuple[DocumentHierarchicalLevel | None, list[str]]:
        """Try to create a sublevel from parts[0] (name) and parts[1] (content).
        Returns (new_sublevel, remaining_parts) tuple."""
        if len(parts) < 2:
            return None, parts
        new_sublevel_name = self.level_splitter.get_sublevel_name(parts[0])
        if not new_sublevel_name:
            return None, parts
        new_sublevel = self.sublevel_factory(new_layout)
        new_sublevel.set_name(TextSanitizer.normalize_chapter_name(new_sublevel_name))
        new_sublevel.append_text(parts[1])
        self.break_level(new_sublevel)
        self.level.add_sublevel(new_sublevel)
        return new_sublevel, parts[2:]

    def _add_table(
        self,
        new_layout: PageLayout,
        current_level: DocumentHierarchicalLevel,
        table_name: str,
    ) -> None:
        """Add to the current level the table that the splitter found by name."""
        table_content = (
            self._table_registry.get(table_name)
            if self._table_registry is not None
            else None
        )
        if table_content is None:
            raise ConverterError(f"Table {table_name!r} is unknown to the registry.")
        table = Table(
            new_layout,
            table_content.name,
            table_content.caption,
            table_content.has_column_headings,
            [list(row) for row in table_content.rows],
        )
        self.break_level(table)
        current_level.add_sublevel(table)

    def _add_heading(
        self,
        new_layout: PageLayout,
        current_level: DocumentHierarchicalLevel,
        title: str,
    ) -> None:
        """Add to the current level the heading that the splitter found."""
        current_level.add_sublevel(
            Heading(new_layout, TextSanitizer.normalize_chapter_name(title))
        )

    def _handle_unbreakable_text(
        self,
        new_layout: PageLayout,
        current_level: DocumentHierarchicalLevel,
        parts: list[str],
    ) -> tuple[bool, list[str]]:
        """Handle text that cannot be broken into sublevels.
        Returns (should_break, remaining_parts) tuple."""
        new_sublevel_type = type(self.sublevel_factory(None))
        remaining = parts[1:]

        if new_sublevel_type == Paragraph:
            part: Part = parts[0]
            if part.kind is PartKind.TABLE:
                self._add_table(new_layout, current_level, part.text)
                return False, remaining
            if part.kind is PartKind.HEADING:
                self._add_heading(new_layout, current_level, part.text)
                return False, remaining
            if not part.text.strip():
                self._diagnostics.warn("Skipping paragraph with empty text.")
                return False, remaining
            paragraph_class = (
                BlockQuoteParagraph if part.kind is PartKind.BLOCKQUOTE else Paragraph
            )
            new_paragraph = paragraph_class(new_layout)
            new_paragraph.append_text(part.text)
            self.break_level(new_paragraph)
            current_level.add_sublevel(new_paragraph)
            return False, remaining

        if new_sublevel_type == SubChapterOfParagraphs:
            # Create a Paragraph directly in the SuperChapter instead of
            # a ChapterOfParagraphs containing a single paragraph.
            self.break_paragraphs(current_level, [TextWithLayout(parts[0], new_layout)])
            return (not remaining), remaining

        raise ConverterError(
            f"Expected Paragraph or ChapterOfParagraphs, got {new_sublevel_type}"
        )

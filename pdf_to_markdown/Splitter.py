import re
from typing import Protocol

import logging

from .Errors import ConverterError
from .TablePlaceholder import TablePlaceholder


class ChapterSplitter:
    """Top level splitter, that is chapter boundary."""

    def __init__(
        self,
        structural_info,
        separator_regex,
        extractor_regex,
        separator_first_occurrence,
    ) -> None:
        self.structural_info = structural_info
        self.separator_regex = separator_regex
        self.extractor_regex = extractor_regex
        self.separator_first_occurrence = separator_first_occurrence

    def holds_new_chapter(self, extracted_page) -> bool:
        # First check static declaration in pages_info
        if self.structural_info._holds_new_chapter(extracted_page.page_number):
            return True
        # A page may be declared not to open a chapter (the regex is fooled by
        # e.g. a centered sub-title followed by blank lines)
        if self.structural_info._forbids_new_chapter(extracted_page.page_number):
            return False
        # Then check regex pattern
        match = re.search(self.separator_regex, extracted_page.text)
        if not match:
            return False
        if match.start() > self.separator_first_occurrence:
            return False
        return True

    def get_chapter_name(self, extracted_page) -> str | None:
        # First check static declaration in pages_info
        if self.structural_info._holds_new_chapter(extracted_page.page_number):
            return self.structural_info._get_chapter_name(extracted_page.page_number)
        # Then use regex extraction
        chapter_name = re.split(self.extractor_regex, extracted_page.text)
        if not chapter_name:
            raise ConverterError(
                f"Chapter name {chapter_name} not found in extracted page {extracted_page.text}"
            )
        return chapter_name[0]

    def extract_chapter_name(self, extracted_page, chapter_name) -> None:
        """Remove chapter name from page text."""
        # removeprefix (and not lstrip) because lstrip treats its argument as
        # a set of characters and would also eat the leading characters of the
        # body text that happen to belong to the chapter name.
        extracted_page.text = extracted_page.text.removeprefix(chapter_name)


class BlockquoteText(str):
    """The text of a part, produced by a splitter, that is a blockquote.

    This is a plain str (the splitters return lists of str) whose only purpose
    is to carry the information "this part is a blockquote" along with the
    text, see Splitter.is_blockquote().
    """


class TableText(str):
    """The text of a part, produced by a splitter, that stands for a table.

    The text is the name of the table, as found in the TablePlaceholder that
    the TableExtractor left in the text of the page. Like BlockquoteText it is
    a plain str that carries the information "this part is a table" along
    with the text, see Splitter.is_table().
    """


class HeadingText(str):
    """The text of a part, produced by a splitter, that is a heading: the title
    of a sub-section that the hierarchy of levels has no level for.

    Like BlockquoteText it is a plain str that carries the information "this
    part is a heading" along with the text (the title), see
    Splitter.is_heading().
    """


class Splitter:
    _logger = logging.getLogger("pdf_to_markdown")

    def is_blockquote(self, part_text) -> bool:
        """Whether a part returned by split() is a blockquote (and not e.g. a paragraph).

        Splitters that do not detect blockquotes never return one.
        """
        return False

    def is_table(self, part_text) -> bool:
        """Whether a part returned by split() stands for a table (and not e.g. a paragraph).

        Splitters that do not detect tables never return one.
        """
        return False

    def is_heading(self, part_text) -> bool:
        """Whether a part returned by split() is a heading (and not e.g. a paragraph).

        Splitters that do not detect headings never return one.
        """
        return False

    def _find_first_match(self, patterns, content_text) -> re.Match[str] | None:
        """Return first regex match across patterns, or None."""
        for pattern in patterns:
            match = re.search(pattern, content_text)
            if match:
                return match
        return None

    def _holds_new_sublevels(self, patterns, content_text) -> bool:
        return self._find_first_match(patterns, content_text) is not None

    def _split_on_single_pattern(
        self, pattern, content_text, remove_separator=False
    ) -> list[str]:
        resulting_parts = re.split(pattern, content_text)
        if resulting_parts[0] == "":
            # As stated in the documentation of the re package:
            #    If there are capturing groups in the separator and it
            #    matches at the start of the string, the result will start
            #    with an empty string.
            # In which case we thus have to remove the heading empty string.
            del resulting_parts[0]
            # When the breaking pattern occurs at the very beginning of the
            # string, the re.split() list will start with an empty string which
            # was taken care of in the above line. But in this case, the empty
            # string is also followed by the encountered separator. When
            # looking for paragraphs the separator carries no information
            # (there is no equivalent of chapter name) and we can remove it
            # here:
            if remove_separator:
                del resulting_parts[0]  # Above deletion made indexes change
            # As stated in the documentation of the re package, and concerning
            # a match of the separator:
            #    The same holds for the end of the string.
            # (that is the result will end with an empty string)
        if resulting_parts[-1] == "":
            del resulting_parts[-1]
        if resulting_parts[-1] == "\n":
            del resulting_parts[-1]
        return resulting_parts

    def _split(self, patterns, content_text) -> list[str]:
        if not self._holds_new_sublevels(patterns, content_text):
            self._logger.warning("split() was called when there was nothing to split.")
            # Wrap the input in a list because the caller expects the
            # returned value to be the result of re.split() (that is a
            # list())
            return [content_text]
        if len(patterns) > 2:
            # Things were simply not tested with more than two patterns...
            raise ConverterError("Capturing groups ambiguity with too many patterns")
        # As stated in the documentation of the re package:
        #    If capturing parentheses are used in pattern, then the text of
        #    all groups in the pattern are also returned as part of the
        #    resulting list.
        first_parts = self._split_on_single_pattern(
            r"(" + patterns[0] + r")", content_text
        )

        resulting_parts = []
        for part_text in first_parts:
            resulting_parts += self._split_on_single_pattern(
                r"(" + patterns[1] + r")", part_text
            )
        if resulting_parts[-1] == "\n":
            del resulting_parts[-1]
        return resulting_parts

    def _get_sublevel_name(
        self, sublevel_patterns, name_extraction_pattern, content_text
    ) -> str | None:
        match = self._find_first_match(sublevel_patterns, content_text)
        if match:
            # Deal with the multiline case
            sublevel_name = re.search(name_extraction_pattern, match.group(0)).group(0)
            # Strip the pdf layout whitespaces (e.g. centered titles)
            return sublevel_name.strip()
        self._logger.warning("Sublevel name not found.")
        return None


class SinglePatternSplitter(Splitter):
    """A splitter using a single pattern to detect the breaking zone. A second sub-pattern is used to extract the name of the document structural element."""

    def __init__(self, breaking_pattern, name_pattern) -> None:
        self.breaking_pattern = breaking_pattern
        self.name_pattern = name_pattern

    def holds_new_sublevels(self, content_text) -> bool:
        return Splitter._holds_new_sublevels(
            self, [self.breaking_pattern], content_text
        )

    def split(self, content_text) -> list[str]:
        # As stated in the documentation of the re package:
        #    If capturing parentheses are used in pattern, then the text of
        #    all groups in the pattern are also returned as part of the
        #    resulting list.
        return Splitter._split_on_single_pattern(
            self, r"(" + self.breaking_pattern + r")", content_text
        )

    def get_sublevel_name(self, content_text) -> str | None:
        return Splitter._get_sublevel_name(
            self,
            [self.breaking_pattern],
            self.name_pattern,
            content_text,
        )


class MultiplePatternSplitter(Splitter):
    """A splitter using a list of possible patterns to detect the breaking zone. A second sub-pattern is used to extract the name of the document structural element."""

    def __init__(self, breaking_patterns, name_pattern) -> None:
        self.breaking_patterns = breaking_patterns
        self.name_pattern = name_pattern

    def holds_new_sublevels(self, content_text) -> bool:
        return Splitter._holds_new_sublevels(self, self.breaking_patterns, content_text)

    def split(self, content_text) -> list[str]:
        return Splitter._split(self, self.breaking_patterns, content_text)

    def get_sublevel_name(self, content_text) -> str | None:
        return Splitter._get_sublevel_name(
            self,
            self.breaking_patterns,
            self.name_pattern,
            content_text,
        )


class NameLessSinglePatternSplitter(SinglePatternSplitter):
    """When breaking paragraphs into sentences there is no need to extract a name for the Sentence structural element."""

    def __init__(self, breaking_pattern) -> None:
        SinglePatternSplitter.__init__(self, breaking_pattern, "dummy_pattern")

    def split(self, content_text) -> list[str]:
        return Splitter._split_on_single_pattern(
            self, self.breaking_pattern, content_text, remove_separator=True
        )

    def get_sublevel_name(self, dummy_content_text) -> str | None:
        return None


class ParagraphAndBlockquoteSplitter(NameLessSinglePatternSplitter):
    """Breaks a text into paragraphs and blockquotes, preserving reading order.

    A blockquote (e.g. a pull quote of a book page) typically cannot be told
    from the paragraphs by the paragraph breaking pattern: its lines (that are
    not paragraph beginnings) might even match that pattern, thus being broken
    into one paragraph per line. The blockquotes are thus cut out of the text
    first, with their own pattern, and the paragraph breaking pattern is only
    applied to the text surrounding them. The headings (titles of sub-sections
    that have no level of their own) are cut out first, the same way.
    """

    def __init__(
        self, paragraph_breaking_pattern, blockquote_pattern, heading_pattern=None
    ) -> None:
        """
        :param paragraph_breaking_pattern: the pattern separating paragraphs
        :param blockquote_pattern: the pattern matching a whole blockquote
            (including the separation with its surrounding text). Its first
            capturing group is the text of the blockquote.
        :param heading_pattern: optional pattern matching a whole heading
            (including the separation with its surrounding text, the blank
            lines following it included). Its first capturing group is the
            title.
        """
        NameLessSinglePatternSplitter.__init__(self, paragraph_breaking_pattern)
        self.blockquote_pattern = re.compile(blockquote_pattern)
        self.heading_pattern = (
            re.compile(heading_pattern) if heading_pattern is not None else None
        )

    def is_blockquote(self, part_text) -> bool:
        return isinstance(part_text, BlockquoteText)

    def is_heading(self, part_text) -> bool:
        return isinstance(part_text, HeadingText)

    def is_table(self, part_text) -> bool:
        return isinstance(part_text, TableText)

    def split(self, content_text) -> list[str]:
        """Breaks a text into paragraphs, blockquotes and tables.

        The tables are cut out first: each TablePlaceholder (see
        TableExtractor) is a table part, whatever surrounds it.
        """
        parts = []
        position = 0
        for table_match in TablePlaceholder.PATTERN.finditer(content_text):
            parts += self._split_into_paragraphs_and_blockquotes(
                content_text[position : table_match.start()]
            )
            parts.append(TableText(table_match.group("table_name")))
            position = table_match.end()
        parts += self._split_into_paragraphs_and_blockquotes(content_text[position:])
        return parts

    def _split_into_paragraphs_and_blockquotes(self, content_text) -> list[str]:
        if self.heading_pattern is None:
            return self._split_around_blockquotes(content_text)
        parts = []
        position = 0
        follows_heading = False
        for match in self.heading_pattern.finditer(content_text):
            parts += self._split_after_heading(
                content_text[position : match.start()], follows_heading
            )
            parts.append(HeadingText(match.group(1)))
            position = match.end()
            follows_heading = True
        parts += self._split_after_heading(content_text[position:], follows_heading)
        return parts

    def _split_after_heading(self, text, follows_heading) -> list[str]:
        # The text following a heading starts like the text of a page does:
        # without the separator of its first paragraph (the heading pattern
        # holds the blank lines) and, unless it is a blockquote (recognized
        # at the very beginning of a text), without indentation.
        if follows_heading and not self.blockquote_pattern.match(text):
            text = text.lstrip(" ")
        return self._split_around_blockquotes(text)

    def _split_around_blockquotes(self, content_text) -> list[str]:
        parts = []
        position = 0
        for match in self.blockquote_pattern.finditer(content_text):
            parts += self._split_into_paragraphs(content_text[position : match.start()])
            parts.append(BlockquoteText(match.group(1)))
            position = match.end()
        parts += self._split_into_paragraphs(content_text[position:])
        return parts

    def _split_into_paragraphs(self, text_without_blockquote) -> list[str]:
        # The text following a blockquote starts with the separator of the
        # next paragraph. It carries no information and
        # _split_on_single_pattern() only copes with such a leading separator
        # when the breaking pattern holds a capturing group.
        leading_separator = re.match(self.breaking_pattern, text_without_blockquote)
        if leading_separator:
            text_without_blockquote = text_without_blockquote[leading_separator.end() :]
        if not text_without_blockquote.strip():
            return []
        return NameLessSinglePatternSplitter.split(self, text_without_blockquote)

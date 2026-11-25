import re
from abc import ABC, abstractmethod
from .DiagnosticsReporter import DiagnosticsReporter
from .Errors import ConverterError
from .PageInfo import PageInfo
from .TableDeclaration import TableDeclaration
from .TableRegistry import TableRegistry


class StructuralInfoBase(ABC):
    """
    Base class for structural information about a PDF document.

    Subclasses must implement pages_info property returning a dict:
    {
        0: {                                # page number as key
            "type": "chapter",              # "chapter" or "generic"
            "chapter_info": {               # required for "chapter" type
                "name": "Preamble",
                "illumination_delimiter": None,
            },
        },
        1: {
            "type": "generic",
            "drop_page": True,              # optional flag to drop content
            "paragraph_fits_on_page": True, # optional: a paragraph ending
                                            # this page is not continued on
                                            # the next one
            "typo_and_fix": {               # optional: a typo of the pdf
                "typo": "teh",              # extraction (a regular
                "fix": "the",               # expression) and its fix; a list
            },                              # of such dictionaries is accepted
            "blockquote_fits_on_page": True,# optional: a blockquote ending
                                            # this page is not continued on
                                            # the next one
            "table_row_continues": True,    # optional: when a table continues
                                            # on this page, True forces the
                                            # merge of its last row of the
                                            # previous page with its first row
                                            # on this page, False forbids it
                                            # (absent: decided by heuristic)
            "no_new_chapter": True,         # optional: the page does not open
                                            # a chapter, whatever its text
                                            # looks like (e.g. a centered
                                            # sub-title followed by blank lines
                                            # is not a chapter title)
        },
    }

    The package reads this dictionary through page_info(), that checks it
    (see PageInfo): a key that is neither known to the package nor listed in
    EXTRA_PAGE_INFO_KEYS is an error. The derived classes remain free to read
    the dictionary directly for their own keys.
    """

    # Dictionary key constants
    KEY_TYPE = PageInfo.KEY_TYPE
    KEY_CHAPTER_INFO = PageInfo.KEY_CHAPTER_INFO
    KEY_NAME = PageInfo.KEY_NAME
    KEY_DROP_PAGE = PageInfo.KEY_DROP_PAGE
    KEY_TYPO_AND_FIX = PageInfo.KEY_TYPO_AND_FIX
    KEY_TYPO = PageInfo.KEY_TYPO
    KEY_FIX = PageInfo.KEY_FIX
    KEY_TABLE_ROW_CONTINUES = PageInfo.KEY_TABLE_ROW_CONTINUES
    KEY_NO_NEW_CHAPTER = PageInfo.KEY_NO_NEW_CHAPTER

    # The keys that a derived class declares in pages_info for its own use
    # (and reads itself), that the package must not take for typos.
    EXTRA_PAGE_INFO_KEYS: frozenset[str] = frozenset()

    @property
    @abstractmethod
    def pages_info(self) -> dict:
        """Return dict mapping page numbers to their structural info."""
        ...

    @property
    @abstractmethod
    def total_page_number(self) -> int:
        """Return total number of pages in the PDF document."""
        ...

    @property
    def numbered_list_heuristics_enabled(self) -> bool:
        """Whether the heuristics dealing with numbered lists are applied.

        Those heuristics (see NumberedListAnnotator) indent the paragraphs
        belonging to an item of a numbered list or to a nested list, and keep
        an item that starts a page from being merged into the paragraph
        above. Derived classes override this to disable them.
        """
        return True

    @property
    def dropped_sections(self) -> list[str]:
        """Titles of the sections (at any depth) to drop from the document.

        Derived classes override this (a class attribute list is enough) with
        the normalized titles, as produced by
        TextSanitizer.normalize_chapter_name. The default drops nothing.
        """
        return []

    @property
    def table_declarations(self) -> list[TableDeclaration]:
        """The tables of the document (see TableDeclaration).

        Derived classes override this with the declarations of their tables.
        The default declares none, in which case the tables (if any) are left
        in the running text.
        """
        return []

    @property
    def table_registry(self) -> TableRegistry:
        """Where the tables cut out of the pages are kept (see TableExtractor)."""
        if self._table_registry is None:
            self._table_registry = TableRegistry()
        return self._table_registry

    def page_info(self, page_number) -> PageInfo:
        """The checked declaration of a page (see PageInfo).

        A page that pages_info does not declare gets the defaults. All the
        declarations are checked at the first call, hence a wrong declaration
        fails there whichever page is asked for.
        """
        if self._page_infos is None:
            self._page_infos = {
                declared_page_number: PageInfo.from_declaration(
                    declared_page_number, declaration, self.EXTRA_PAGE_INFO_KEYS
                )
                for declared_page_number, declaration in self.pages_info.items()
            }
        return self._page_infos.get(page_number, PageInfo())

    def get_table_row_continues(self, page_number) -> bool | None:
        """The declared decision about the row of a table cut by a page break.

        The page is the one on which the table continues. None when the
        decision is left to the heuristic of the TableExtractor.
        """
        return self.page_info(page_number).table_row_continues

    def is_section_dropped(self, section_name: str) -> bool:
        """Whether a section designated by its normalized title must be dropped.

        The comparison ignores the case.
        """
        folded_name = section_name.casefold()
        return any(
            folded_name == dropped_section.casefold()
            for dropped_section in self.dropped_sections
        )

    def __init__(self) -> None:
        # Technical (optimisation) variable used to hold the correspondance
        # between a given page number and the chapter to which that page
        # belongs to. In other terms, within this dictionary
        #  - a key is a page number
        #  - the associated value holds the current chapter number for that key
        self._chapter_page = {}
        self._chapter_splitter_instance = None
        self._table_registry = None
        # Lazily built by page_info()
        self._page_infos = None
        self._diagnostics = DiagnosticsReporter()

    def set_diagnostics(self, diagnostics: DiagnosticsReporter) -> None:
        self._diagnostics = diagnostics

    def get_chapter_splitter(self):
        """Get or create the chapter splitter for this document.

        Each derived StructuralInfo defines a chapter_splitter inner class.
        """
        if self._chapter_splitter_instance is None:
            self._chapter_splitter_instance = self.chapter_splitter(self)
        return self._chapter_splitter_instance

    def set_chapter_page_number(
        self, page_number: int, chapter_page_number: int
    ) -> None:
        """Set the chapter page number of the page designated by page number.

        :param int page_number: The page number of the page for which we are setting the chapter (page)
        :param int chapter_page_number The page number of the chapter (beginning) to which the designated belongs to.
        """
        if page_number in self._chapter_page:
            raise ConverterError(
                f"Trying to overwrite chapter page of page number {page_number}."
            )
        self._chapter_page[page_number] = chapter_page_number

    def _page_is_dropped(self, page_number) -> bool:
        return self.page_info(page_number).drop_page

    def _page_is_skipped(self, page_number) -> bool:
        """
        The derived classes might overload this definition with their specific considerations.
        """
        return self._page_is_dropped(page_number)

    def _get_chapter_page_number(self, page_number) -> int:
        if page_number not in self._chapter_page:
            raise ConverterError(f"Unknown chapter page of page number {page_number}.")
        return self._chapter_page[page_number]

    def _get_chapter_page(self, page_number) -> dict:
        chapter_page_number = self._get_chapter_page_number(page_number)
        return self.pages_info[chapter_page_number]

    def _get_chapter_info(self, page_number) -> dict:
        chapter_page = self._get_chapter_page(page_number)
        return chapter_page[self.KEY_CHAPTER_INFO]

    def _get_chapter_name(self, page_number) -> str | None:
        chapter_page_number = self._get_chapter_page_number(page_number)
        return self.page_info(chapter_page_number).chapter_name

    def _forbids_new_chapter(self, page_number) -> bool:
        """Whether the page is declared not to open a chapter (see
        ChapterSplitter.holds_new_chapter), whatever its text looks like."""
        return self.page_info(page_number).no_new_chapter

    def _holds_new_chapter(self, page_number) -> bool:
        return self.page_info(page_number).is_chapter

    def fix_typos(self, extracted_page) -> None:
        """Apply typo fixes on extracted pages that require it."""
        page_number = extracted_page.page_number
        for typo_fix in self.page_info(page_number).typo_fixes:
            typo = typo_fix.typo
            fixed_text, substitution_count = re.subn(
                typo, typo_fix.fix, extracted_page.text
            )
            if substitution_count == 0:
                self._diagnostics.warn(
                    f"Couldn't find typo in extracted page number {page_number}:"
                )
                self._diagnostics.warn(f"  - typo: {typo}")
                self._diagnostics.warn(f"  - page text: {extracted_page.text}")
                continue
            extracted_page.text = fixed_text
            self._diagnostics.debug(f"Typo fixed on page {page_number}")

    def _get_page_number_finishing_last_paragraph(self, page_number) -> int:
        """
        A page that is followed by one (or many) skipped pages will need to skip such pages in order to retrieve the end of its last paragraph.
        Return the page number of the first page that holds the content of the end of the paragraph.
        """
        next_page_number = page_number + 1
        while self._page_is_skipped(next_page_number):
            next_page_number += 1
        return next_page_number

    def convert_to_logical_page_number(self, page_number) -> str:
        """
        Some pdf books (generally also available in paper form) propose an
        ad-hoc page numbering scheme (think e.g. of roman numbering based page numbers or starting the numbering after the pages holding the editor's
        notes). There is thus a correspondance between the page number at the
        pdf language level (that always exists) and the optional editor's page numbering.
        Parameters
        ----------
        page_number : int
            the page number at the PDF level
        Returns
        -------
        the page number (as string) as printed on the page (editor's choice)
        """
        return str(page_number)

    def sanitize_page_text(self, extracted_page) -> None:
        """Sanitize page text. Override in derived classes for book-specific sanitization."""
        pass

    def strip_page_text_leading_whitespace(self, page_text: str) -> str:
        """Remove the leading whitespace of the text extracted from a page.

        The default removes all of it. A derived class that must keep the
        indentation of the first line of a page (e.g. when a blockquote starts
        at the very top of a page and is recognized by its indentation) can
        override this method. Note that the chapter detection of the text
        extracted from a page (holds_new_chapter, extract_chapter_name) assumes
        text without leading whitespace.
        """
        return page_text.lstrip()

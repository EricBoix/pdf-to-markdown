from abc import ABC, abstractmethod
from .Errors import ConverterError
from .PageInfo import PageInfo
from .TableDeclaration import TableDeclaration
from .typo_rules import TypoRule, TypoRuleRegister, TypoRuleStatus


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

    # The rule configuration section of a document: the names of the
    # typographic rules (see typo_rules.TypoRule) that hold for the document, and
    # those that do not. A rule that is in neither set is unknown to the document
    # (see rule_status). Derived classes override them, a class attribute is
    # enough. An implicit rule (always true) is never declared.
    valid_rules: frozenset[str] = frozenset()
    rejected_rules: frozenset[str] = frozenset()

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

    def rule_status(self, rule_name: str) -> TypoRuleStatus:
        """What the document declares about a typographic rule: HOLDS when the
        name is in valid_rules (an implicit rule always holds), DOES_NOT_HOLD
        when it is in rejected_rules, UNKNOWN otherwise.

        A name that is not the one of a rule is an error: it is a typo.
        """
        if not self.rule_register.get(rule_name).configurable:
            return TypoRuleStatus.HOLDS
        if rule_name in self.valid_rules:
            return TypoRuleStatus.HOLDS
        if rule_name in self.rejected_rules:
            return TypoRuleStatus.DOES_NOT_HOLD
        return TypoRuleStatus.UNKNOWN

    def rule_holds(self, rule_name: str) -> bool:
        return self.rule_status(rule_name) is TypoRuleStatus.HOLDS

    def rule_if_holds(self, rule_name: str) -> TypoRule | None:
        """The rule when the document holds it, None otherwise. This is how the
        code that acts on a rule gets it: the rules flow from the structural
        information (rule_register), the code never builds a register of its
        own."""
        if not self.rule_holds(rule_name):
            return None
        return self.rule_register.get(rule_name)

    def _check_rule_declarations(self) -> None:
        """Refuse a declaration naming no rule, an implicit rule, or a rule that
        is both valid and rejected."""
        for rule_name in self.valid_rules | self.rejected_rules:
            if not self.rule_register.get(rule_name).configurable:
                raise ConverterError(
                    f"The rule {rule_name} is implicit (always true): "
                    "a document does not declare it."
                )
        both = self.valid_rules & self.rejected_rules
        if both:
            raise ConverterError(
                f"The rules {sorted(both)} are declared both valid and rejected."
            )

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
        # A StructuralInfo is configuration only: it is the same from one
        # conversion to the next and holds nothing that a conversion produces.
        # (The correspondance between a given page number and the chapter to
        # which that page belongs used to be held here, as a technical
        # variable. It now stands on the extracted page itself, see
        # ExtractedPage.chapter_name and ExtractedPage.chapter_page_number. The
        # tables cut out of the pages are kept by the converter.)
        # What follows are caches of values derived from the configuration,
        # built on demand:
        self._chapter_splitter_instance = None
        # See page_info()
        self._page_infos = None
        # The typographic rules, handed to the code that acts on them (the only
        # place where the register of the package is built)
        self.rule_register = TypoRuleRegister.default()
        self._check_rule_declarations()

    def get_chapter_splitter(self):
        """Get or create the chapter splitter for this document.

        Each derived StructuralInfo defines a chapter_splitter inner class.
        """
        if self._chapter_splitter_instance is None:
            self._chapter_splitter_instance = self.chapter_splitter(self)
        return self._chapter_splitter_instance

    def _page_is_dropped(self, page_number) -> bool:
        return self.page_info(page_number).drop_page

    def _page_is_skipped(self, page_number) -> bool:
        """
        The derived classes might overload this definition with their specific considerations.
        """
        return self._page_is_dropped(page_number)

    def _get_chapter_info(self, chapter_page_number) -> dict:
        """The raw chapter_info declared by the page that opens a chapter (the
        page itself for a page that does open one, see ExtractedPage)."""
        return self.pages_info[chapter_page_number][self.KEY_CHAPTER_INFO]

    def _get_chapter_name(self, chapter_page_number) -> str | None:
        """The name declared by the page that opens a chapter."""
        return self.page_info(chapter_page_number).chapter_name

    def _forbids_new_chapter(self, page_number) -> bool:
        """Whether the page is declared not to open a chapter (see
        ChapterSplitter.holds_new_chapter), whatever its text looks like."""
        return self.page_info(page_number).no_new_chapter

    def _holds_new_chapter(self, page_number) -> bool:
        return self.page_info(page_number).is_chapter

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

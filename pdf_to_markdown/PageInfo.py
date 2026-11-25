from dataclasses import dataclass

from .Errors import ConverterError


@dataclass(frozen=True)
class TypoFix:
    """A regular expression matching a typo that the pdf extraction produced,
    and what to replace it with."""

    typo: str
    fix: str


@dataclass(frozen=True)
class PageInfo:
    """What a StructuralInfoBase declares about one page.

    The declaration itself is a dictionary (see StructuralInfoBase.pages_info)
    that the derived classes write by hand. This is the checked, typed view of
    that dictionary that the rest of the package reads: the keys are checked
    once, and each of them is read the same way everywhere (an absent key is
    the default of the corresponding field).
    """

    KEY_TYPE = "type"
    KEY_CHAPTER_INFO = "chapter_info"
    KEY_NAME = "name"
    KEY_DROP_PAGE = "drop_page"
    KEY_TYPO_AND_FIX = "typo_and_fix"
    KEY_TYPO = "typo"
    KEY_FIX = "fix"
    KEY_TABLE_ROW_CONTINUES = "table_row_continues"
    KEY_NO_NEW_CHAPTER = "no_new_chapter"
    KEY_PARAGRAPH_FITS_ON_PAGE = "paragraph_fits_on_page"
    KEY_BLOCKQUOTE_FITS_ON_PAGE = "blockquote_fits_on_page"

    TYPE_CHAPTER = "chapter"

    KNOWN_KEYS = frozenset(
        {
            KEY_TYPE,
            KEY_CHAPTER_INFO,
            KEY_DROP_PAGE,
            KEY_TYPO_AND_FIX,
            KEY_TABLE_ROW_CONTINUES,
            KEY_NO_NEW_CHAPTER,
            KEY_PARAGRAPH_FITS_ON_PAGE,
            KEY_BLOCKQUOTE_FITS_ON_PAGE,
        }
    )

    # The declared "type" of the page ("chapter", "generic" or whatever a
    # derived class declares, e.g. "illustration"). None when not declared.
    kind: str | None = None
    # The name of the chapter that the page opens (a "chapter" type page).
    chapter_name: str | None = None
    drop_page: bool = False
    typo_fixes: tuple[TypoFix, ...] = ()
    # Tri-state: None leaves the decision to the heuristic of the
    # TableExtractor.
    table_row_continues: bool | None = None
    no_new_chapter: bool = False
    paragraph_fits_on_page: bool = False
    blockquote_fits_on_page: bool = False

    @property
    def is_chapter(self) -> bool:
        return self.kind == self.TYPE_CHAPTER

    @classmethod
    def from_declaration(
        cls,
        page_number: int,
        declaration: dict,
        extra_keys: frozenset[str] = frozenset(),
    ) -> "PageInfo":
        """Check the declaration of a page and build its PageInfo.

        :param extra_keys: the keys that a derived StructuralInfoBase declares
            for its own use, that the package ignores (see
            StructuralInfoBase.EXTRA_PAGE_INFO_KEYS).
        """
        unknown_keys = set(declaration) - cls.KNOWN_KEYS - extra_keys
        if unknown_keys:
            raise ConverterError(
                f"Page {page_number} declares unknown key(s) {sorted(unknown_keys)}, "
                f"known keys are {sorted(cls.KNOWN_KEYS | extra_keys)}."
            )
        page_type = declaration.get(cls.KEY_TYPE)
        chapter_info = declaration.get(cls.KEY_CHAPTER_INFO)
        if page_type == cls.TYPE_CHAPTER:
            if chapter_info is None:
                raise ConverterError(
                    f"Chapter page {page_number} missing chapter_info."
                )
            if cls.KEY_NAME not in chapter_info:
                raise ConverterError(
                    f"Chapter page {page_number} missing name in chapter_info."
                )
        return cls(
            kind=page_type,
            chapter_name=(
                chapter_info.get(cls.KEY_NAME) if chapter_info is not None else None
            ),
            drop_page=bool(declaration.get(cls.KEY_DROP_PAGE, False)),
            typo_fixes=cls._get_typo_fixes(page_number, declaration),
            table_row_continues=declaration.get(cls.KEY_TABLE_ROW_CONTINUES),
            no_new_chapter=bool(declaration.get(cls.KEY_NO_NEW_CHAPTER, False)),
            paragraph_fits_on_page=bool(
                declaration.get(cls.KEY_PARAGRAPH_FITS_ON_PAGE, False)
            ),
            blockquote_fits_on_page=bool(
                declaration.get(cls.KEY_BLOCKQUOTE_FITS_ON_PAGE, False)
            ),
        )

    @classmethod
    def _get_typo_fixes(
        cls, page_number: int, declaration: dict
    ) -> tuple[TypoFix, ...]:
        typo_and_fix = declaration.get(cls.KEY_TYPO_AND_FIX)
        if typo_and_fix is None:
            return ()
        # Accept either a single fix dict or a list of fix dicts.
        fix_entries = typo_and_fix if isinstance(typo_and_fix, list) else [typo_and_fix]
        typo_fixes = []
        for fix_entry in fix_entries:
            for key in (cls.KEY_TYPO, cls.KEY_FIX):
                if key not in fix_entry:
                    raise ConverterError(
                        f"Page {page_number} typo_and_fix entry missing {key!r}."
                    )
            typo_fixes.append(TypoFix(fix_entry[cls.KEY_TYPO], fix_entry[cls.KEY_FIX]))
        return tuple(typo_fixes)

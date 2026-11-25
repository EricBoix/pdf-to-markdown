from .Model import DocumentHierarchicalLevel, Heading, Paragraph, Table
from .DiagnosticsReporter import DiagnosticsReporter
from .Errors import ConverterError
from .StructuralInfoBase import StructuralInfoBase


class SectionDropper:
    """Drops the sections (chapters, sub-chapters...) a converter asks to drop.

    The sections to drop are designated by their title: the converter declares
    them in the dropped_sections of its StructuralInfoBase derived class (see
    StructuralInfoBase.is_section_dropped for the matching rules). Every level
    carrying a designated title is dropped, at any depth, together with all
    its sublevels.

    The sections are dropped once the whole hierarchy is built, and not when
    the titles are met, because the pages of a dropped section must still be
    attributed to their chapter during the breaking of the document.

    This is meant to be applied before the paragraphs spreading over two pages
    are reconstituted (see ParagraphMerger), so that a paragraph is never
    glued to the text of a dropped section.
    """

    def __init__(
        self,
        structural_info: StructuralInfoBase,
        diagnostics: DiagnosticsReporter | None = None,
    ) -> None:
        self._structural_info = structural_info
        self._diagnostics = DiagnosticsReporter.default_if_none(diagnostics)
        # The (casefolded) dropped titles that were met in the document
        self._matched_titles: set[str] = set()

    def _drop_from(self, level: DocumentHierarchicalLevel) -> None:
        for sublevel in list(level.get_sublevels() or []):
            # Paragraphs are nameless: their name is a mere placeholder that
            # must not be mistaken for a section title. Neither is a table or a
            # heading (a leaf with no sublevels).
            if isinstance(sublevel, (Paragraph, Table, Heading)):
                continue
            if self._structural_info.is_section_dropped(sublevel.name):
                self._diagnostics.debug(f"Dropping section: {sublevel.name!r}")
                self._matched_titles.add(sublevel.name.casefold())
                level.remove_sublevel(sublevel)
                continue
            self._drop_from(sublevel)
        level.renumber_sublevels()

    def drop_sections(self, document) -> None:
        self._matched_titles = set()
        self._drop_from(document)
        unmatched_titles = [
            title
            for title in self._structural_info.dropped_sections
            if title.casefold() not in self._matched_titles
        ]
        if unmatched_titles:
            raise ConverterError(
                f"Sections to drop not found in the document: {unmatched_titles}"
            )

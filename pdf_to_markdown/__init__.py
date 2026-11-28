import logging

# Library convention: stay silent unless the application configures logging.
logging.getLogger("pdf_to_markdown").addHandler(logging.NullHandler())

from .Model import (
    Sentence,
    Paragraph,
    BlockQuoteParagraph,
    Table,
    Heading,
    PageBreak,
    TopLevelChapterOfParagraphs,
    SubChapterOfParagraphs,
    SuperChapter,
    DocumentHierarchicalRoot,
    DocumentWithSubChapters,
    Document,
    PublicationInfo,
)
from .NumberedListAnnotator import (
    NumberedListAnnotator,
    NumberedListPlacement,
    NumberedListRole,
)
from .LineWrapper import LineWrapper
from .ConverterBase import ConverterBase
from .DocumentBuilder import DocumentBuilder
from .DocumentBreaker import DocumentBreaker
from .TextExtractor import TextExtractor
from .TextSanitizer import TextSanitizer
from .ParagraphMerger import ParagraphMerger
from .ExtractedPage import ExtractedPage
from .PageInfo import PageInfo, TypoFix
from .TypoFixer import TypoFixer
from .SentenceBreaker import SentenceBreaker
from .typo_rules import (
    TypoRule,
    TypoRuleForMerge,
    TypoRuleRegister,
    TypoRuleStatus,
    TypoRuleVerdict,
)
from .StructuralInfoBase import StructuralInfoBase
from .Splitter import (
    ChapterSplitter,
    SinglePatternSplitter,
    Splitter,
    MultiplePatternSplitter,
    NameLessSinglePatternSplitter,
    ParagraphAndBlockquoteSplitter,
)
from .Part import Part, PartKind
from .DebugComments import DebugComments
from .PageMarker import PageMarker
from .TableDeclaration import TableDeclaration
from .TableExtractor import TableExtractor
from .TableLayoutParser import TableLayoutParser
from .TablePlaceholder import TablePlaceholder
from .TableRegistry import SpanningCellText, TableContent, TableRegistry
from .BlockquoteDeduplicator import BlockquoteDeduplicator
from .PageBreakInserter import PageBreakInserter
from .SectionDropper import SectionDropper
from .PageLayout import PageLayout
from .Errors import ConverterError
from .Traces import (
    PrintDocument,
    print_document_raw_pages,
)

from .MarkdownToDocument import MarkdownToDocument

# Configurable rules

The typographic rules that code relies on and that a book declares. A document
declares them in the rule configuration section of its structural information
(a class derived from `StructuralInfoBase`):

```python
class StructuralInfo(StructuralInfoBase):
    valid_rules = frozenset({"LowercaseTailContinues", "UnpunctuatedHeadContinues"})
    rejected_rules = frozenset()
```

A rule can be in one of three states for a document:

- `HOLDS`: the rule is in `valid_rules`. The code acts on it and checks it.
- `DOES_NOT_HOLD`: the rule is in `rejected_rules`. The code ignores it.
- `UNKNOWN`: the rule is in neither. The code ignores it. Declaring nothing
  never changes what the converter does.

An unknown name, a name in both sets, or the name of an implicit rule makes the
structural information fail at construction.

A rule declared by mistake is detected: each rule that holds is also asked whether
a page break contradicts it, and the converter warns about it (the logger
`pdf_to_markdown`, see `DiagnosticsReporter`). The warning never changes the
conversion.

The candidate rules are in [rules_possible.md](rules_possible.md), the rules that
hold for every book in [rules_implicit.md](rules_implicit.md).

## Rules deciding whether a page continues a paragraph

`ParagraphMerger` looks at the last sentence of the head (what ends a page) and
the first sentence of the tail (what starts the next one). It asks the rules that
hold, in the order below. The first verdict that is not "no opinion" decides.
When no rule decides, the paragraphs are not merged: a false split leaves a
paragraph in two pieces, a false merge glues a sentence onto another page (a
design preference, not a rule).

A sentence is complete when it ends with `.`, `!`, `?` or an ellipsis, possibly
followed by closing quotes or brackets and by a footnote number.

### LowercaseTailContinues

A lowercase start on the next page continues the paragraph of the page before.

- **Code:** `typo_rules/LowercaseTailContinues.py`.
- **Trap:** a lowercase start after a complete last sentence.

### UnpunctuatedHeadContinues

A last sentence without terminal punctuation continues on the next page.

- **Code:** `typo_rules/UnpunctuatedHeadContinues.py`.
- **Trap:** an uppercase start after such a last sentence.

### CompleteHeadUppercaseTailStartsParagraph

A complete last sentence followed by an uppercase start on the next page begins
a new paragraph.

- **Code:** `typo_rules/CompleteHeadUppercaseTailStartsParagraph.py`.
- **Trap:** none yet: nothing in the text of the two sentences tells that such a
  page break is a continuation.

## ReadingOrderIsLineOrder

The reading order of a page is the extractor's line order (top to bottom, one text
flow). The converter relies on it wherever it reads the text of a page.

- **Exceptions inside it:** floats such as pull quotes and the text of an
  illustration, interleaved in line order inside a paragraph.
- **Code:** `typo_rules/ReadingOrderIsLineOrder.py`; action site
  `PageBreakInserter` (it gets the rule from the structural information only when
  the document declares it).
- **Trap:** `ReadingOrderIsLineOrder.order_violations`: the pages of the page
  breaks must strictly increase. The order of the pages only, not the order
  inside a page.

## SpacedEllipsisIsAnEllipsis

Dots separated by spaces (". . .") are one ellipsis, spelled "...". The sentence
tokenizer would otherwise cut it into one sentence per dot.

- **Code:** `typo_rules/SpacedEllipsisIsAnEllipsis.py`; action site
  `TextExtractor.extract_all`. Without the rule the dots are left as they are.
- **Trap:** the number of spaced ellipses of each page is reported (debug).

## LayoutTextCarriesIndentationAndColumns

The text extracted by pypdf in layout mode keeps what the patterns of a book read:
the indentation of a line, the centering of a title, the columns of a table.

- **Code:** `typo_rules/LayoutTextCarriesIndentationAndColumns.py`; action site
  `TextExtractor.extract_all`.
- **Trap:** a page that pypdf cannot extract in layout mode falls back to plain
  text: the converter warns, naming the page.

## BlockquoteRepeatingParagraphIsDropped

A pull quote made of one or more complete sentences of a paragraph of the same,
the previous or the next page is a duplicate and is dropped. The rule removes text
from the document.

- **Code:** `typo_rules/BlockquoteRepeatingParagraphIsDropped.py`; action site
  `BlockquoteDeduplicator`. Without the rule no blockquote is dropped.
- **Trap:** each dropped blockquote is reported with its page (debug).

## NumberedItemStartingAPageIsNotAContinuation

The numbering of a document is trustworthy, its layout is not: a paragraph that
starts a page with the number following the last item above is the next item, not
the end of a cut paragraph; a numbering that restarts at 1 inside an open list is
a nested list; a paragraph between two items belongs to the item above.

- **Code:** `typo_rules/NumberedItemStartingAPageIsNotAContinuation.py`; action
  sites `ParagraphMerger` and the annotation of the numbered lists of a level
  (`ConverterBase` sets the flag of the document from the rule). It replaces the
  former `StructuralInfoBase.numbered_list_heuristics_enabled`.
- **Trap:** a numbered item that belongs to no list is kept and reported
  (`NumberedListAnnotator`).

## TableRowCutHasEmptyCellAndLowercaseStart

A row of a table was cut by a page break when a cell is empty in the last row of
the page while it holds text in the first row of the next page, and a cell of
that first row starts with a lowercase letter. The declaration of a page
(`table_row_continues`) wins over the rule.

- **Code:** `typo_rules/TableRowCutHasEmptyCellAndLowercaseStart.py`; action site
  `TableExtractor._decide_row_continuation`. Without the rule a row is merged
  only when the page declares it.
- **Trap:** the decision and its reason are reported for each page break of a
  table (warning).

## DiacriticsFoldToBaseLetters

The letters carrying a diacritic that a book uses (the transliteration of a
language, for instance) fold to the closest ASCII base letter.

- **Code:** `typo_rules/DiacriticsFoldToBaseLetters.py`; action site
  `TextExtractor.extract_all` (and the declared names of the chapters,
  `DocumentBreaker`), through `TextSanitizer.sanitize_characters`. The letters
  are those of `StructuralInfoBase.diacritic_foldings` (a book overrides it; the
  default is `DiacriticsFoldToBaseLetters.DEFAULT_FOLDINGS`). Without the rule
  nothing is folded.
- **Trap:** a character that is still not ASCII once folded is reported with its
  page. The output is thus not always plain ASCII: the books converted so far
  keep a few characters (letters of another alphabet, an en space, an arrow)
  that no folding covers.

## SmileyGlyphsFoldToAnEmoticon

The white smiling face and the private-use glyph U+F04A that some PDF fonts use
for a smiley both fold to ":-)". The meaning of U+F04A depends on the font of the
book, hence the declaration.

- **Code:** `typo_rules/SmileyGlyphsFoldToAnEmoticon.py`; action site
  `TextExtractor.extract_all`, through `TextSanitizer.sanitize_characters`.
- **Trap:** none: a glyph that the rule does not know is reported by the trap of
  `DiacriticsFoldToBaseLetters` when the document holds it.

## Which book declares which rule

Each book declares its rules in the structural information it derives from
`StructuralInfoBase`. This package does not know which books use it.

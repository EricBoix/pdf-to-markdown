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

## Which book declares which rule

Each book declares its rules in the structural information it derives from
`StructuralInfoBase`. This package does not know which books use it.

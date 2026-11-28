# Possible rules

A typographic convention is local to a book: a rule can hold for one book and
fail for another, so none is assumed for all of them. This file lists the
candidate rules, the ones that no code relies on yet, with the evidence found
for and against each. Nothing is claimed that was not read on a page.

When code relies on a rule, it becomes a class of `pdf_to_markdown.typo_rules`
and moves to [rules_configurable.md](rules_configurable.md). The rules that hold
for every book, by design, are in [rules_implicit.md](rules_implicit.md).

A rule is named by a slug, which is the name of its class. There is no number
and no order among the rules.

The evidence that depends on a given book (which pages, which quotes) belongs
to that book, with the structural information that declares its rules. Only
what holds across books, or what is measured, is kept here.

## IndentedTailStartsParagraph

A first-line indent begins a new paragraph.

- **Status:** not used by the code. The extractor records the indentation it
  removes (`removed_first_line_indentations`, `ExtractedPage`), but only
  `TableExtractor` reads it. The paragraph merger ignores it. Nothing says yet
  that the layout text gives a usable indent against the margin of the page.
- **Not universal:** a book may indent no paragraph, or all of them.
- **Seen:** a paragraph opening a page with a first-line indent, after a
  paragraph ending with a footnote number, was a new paragraph and not a
  continuation.
- **Spike before any use:** check, on each book, whether the layout text gives
  the indent of the first line of a page against the margin of its other lines.

## DigitsAfterPunctuationAreFootnotes

Digits right after sentence punctuation are footnote numbers (as in
"...in the same system.11").

- **Status:** documentation only, not a class and not declarable. The converter
  does tolerate such digits after the terminal punctuation of the last sentence
  of a page (see `TypoRuleForMerge.TERMINAL_PUNCTUATION`), for every book: it is
  fixed there, not configured. Promoting this rule to a class moves that
  tolerance out of the merge rules; that is left to another plan.
- **Followed:** in one of the books converted so far, 239 spans are footnote
  references: superscript, smaller than the text (size 10.8 against 14.4) and
  coloured. 160 follow `. ! ?`.
- **Not covered by this shape:** in that book, 20 follow a closing quote or
  bracket (")17"), 25 follow `, ; :` ("seven years,2") and 34 follow a letter
  ("absorption7"). The digits-after-punctuation shape covers 160 of the 239
  footnote references.
- **Unknown for the other books:** in two other books no digit span follows
  sentence punctuation, so the rule never fires there.
- **Risk:** a sentence cut right after a decimal number ("...costs 3.5") has the
  shape of a footnote reference. None was seen so far.

## TypographySignalsIdentifyFootnotes

The font size, the superscript flag and the colour of a span identify a
footnote reference, whatever the characters around it.

- **Status:** not used by the code. The text extractor reads the layout text of
  pypdf and discards size, flags and colour before any decision is made.
- **Available:** in the book of the 239 spans above.
- **Absent after sentence punctuation:** in the two other books.
- **Spike before any use:** carry the spans through the existing extractor, or
  change the extraction path.

## IllustrationRepeatingBodyIsDropped

An illustration page whose only text repeats a passage of the body is dropped
without loss of content.

- **Status:** it drives the per-page declaration `drop_page` of a book, which
  the book itself writes (see `StructuralInfoBase`). No rule class is needed
  until the converter checks the claim.
- **Followed:** by the pages a book declares dropped, because the text of the
  illustration is an extracted quote of the body.
- **Not followed:** by an illustration page whose text is original: the page is
  kept.

## Found by reading the converter

What follows was found by reading the modules of the package and the hooks a
book supplies (not by measuring a book): every behaviour that rests on a belief
about typography. Each entry is a candidate. Nothing changes in the code until
each one is accepted, rejected or split. An accepted entry becomes a class with
an action site and a trap, like the rules of
[rules_configurable.md](rules_configurable.md).

For each entry: the statement, where the code acts, its status (**hardwired**:
the same for every book; **declared**: the book says it, as data or as a pattern
of its own code, without going through `valid_rules`; **not used**), and what
accepting it would mean. A "proposal" has been accepted by the owner of the
project; it is carried out one rule at a time, each in its own change.

Already carried out, they moved to [rules_configurable.md](rules_configurable.md):
`SpacedEllipsisIsAnEllipsis`, `LayoutTextCarriesIndentationAndColumns`,
`BlockquoteRepeatingParagraphIsDropped`,
`NumberedItemStartingAPageIsNotAContinuation`,
`TableRowCutHasEmptyCellAndLowercaseStart`, `DiacriticsFoldToBaseLetters` and
`SmileyGlyphsFoldToAnEmoticon`. The proposals to keep as a fact (`TabsAreSpaces`,
`TypographicQuotesAndDashesFoldToAscii`) moved to
[rules_implicit.md](rules_implicit.md).

### Hardwired: the characters

### Hardwired: the text of a paragraph

#### NewlineInTextIsLineFolding

A newline inside the text of a paragraph or of a sentence is a line wrap, and
becomes a space; runs of whitespace become one space.

- **Where:** `TextSanitizer.normalize_newlines_and_multiple_whitespaces`.
- **Status:** hardwired. The paragraph boundary is decided before, by the
  pattern of the book (see `IndentedLineStartsParagraph`).
- **Not the same everywhere:** a hyphen ending a line stays in the running text
  with a space after it (the documentation of `BlockquoteDeduplicator` cites
  "non- perceiving"), whereas the cells of a table glue the two pieces of a
  hyphenated word (`TableLayoutParser.join_wrapped_text`, see the next entry).

#### LineEndingHyphenJoinsTheWordInTableCells

A table cell wrapped on many lines is one text, and a hyphen ending a piece
glues it to the next piece without a space ("fame-" "obscurity").

- **Where:** `TableLayoutParser.join_wrapped_text`.
- **Status:** hardwired. Nothing tells a hyphen added by the typesetter from the
  hyphen of a compound word, and both are glued.
- **Proposal:** documentation only until a counter-example is seen.

#### UppercaseNameSplitAcrossLinesIsOneWord

A newline between two uppercase letters, the second followed by an uppercase
letter, is a split inside a word of a title ("GET" "TING").

- **Where:** `TextSanitizer.normalize_chapter_name`.
- **Status:** hardwired. Applies to titles in capitals only.
- **Proposal:** keep as a fact of the extractor; add a trap when the glued name
  contains a word that no capital title would have.

#### WordTerminalApostropheIsAmbiguous

A letter followed by an apostrophe and a space, in a sentence that opens with an
apostrophe, may be a possessive or a closing quote: the sentence is framed with
mismatch markers instead of being guessed.

- **Where:** `TextSanitizer.frame_sentences_if_unbalanced`, called by
  `SentenceBreaker`.
- **Status:** hardwired (the decision is *not to decide*, and to say so).
- **Proposal:** keep: it is a trap, already.

#### SentencesEndWhereTheEnglishTokenizerSaysSo

The boundaries between the sentences of a paragraph are those of the NLTK
sentence tokenizer (English).

- **Where:** `SentenceBreaker.break_into_sentences`.
- **Status:** hardwired. A book in another language is cut by English rules.
- **Proposal:** configurable (the language of the book). The page break rules
  (`TERMINAL_PUNCTUATION`) are English as well.

### Hardwired: the extraction

#### PageTextLeadingWhitespaceIsMargin

The whitespace before the first line of a page is the margin of the page, not
text, and is stripped.

- **Where:** `StructuralInfoBase.strip_page_text_leading_whitespace` (default
  `lstrip`), whose result `TextExtractor` compares with the original to record
  `removed_first_line_indentations`.
- **Status:** hardwired by default, overridable by a book that needs the indent
  of the first line (a pull quote or a centered title at the very top of a
  page).
- **Proposal:** the override is the book saying "the indent of the first line of
  a page carries information": the same belief as
  `IndentedTailStartsParagraph`. Decide them together.

### Hardwired: the page breaks and the tree

#### ParagraphMayContinueOnTheNextPageUnlessDeclared

A page that declares nothing may end with a paragraph (or a blockquote) that the
next page continues. A page flagged `paragraph_fits_on_page` or
`blockquote_fits_on_page` is the declared exception.

- **Where:** `ParagraphMerger._page_requires_paragraph_continuation`,
  `_page_requires_blockquote_continuation`. The code comment itself calls it
  "a bit ambitious".
- **Status:** hardwired default, declared per page. The merge rules then decide
  whether the paragraph really continues.
- **Proposal:** keep (the merge rules are the filter); the per-page flags are
  data, listed below.

#### TableOrHeadingBetweenInterruptsTheTextFlow

When a table or a heading comes between the last paragraph of a page and the
first of the next one, the two paragraphs are not merged.

- **Where:** `ParagraphMerger._table_lies_between`.
- **Status:** hardwired.
- **Proposal:** keep as a fact (a sentence announcing a table is not continued
  by the paragraph that comments it): the rule is the reason, the code is the
  action site.

#### TableColumnsAreSeparatedByGutters

The columns of a table are the stretches of the layout text separated by a gutter
of at least a declared width of blank positions, the same on every line.

- **Where:** `TableLayoutParser._find_column_starts`, the width being declared
  by each table.
- **Status:** declared (width and patterns of each table).
- **Proposal:** none: it is a parameter of a table, not a belief of the book.

### Declared by the book, as patterns or hooks

The package cannot hold these (it knows no book). It can name the belief, so
that a book declares it as a rule instead of burying it in a pattern.

#### ChapterTitleStartsThePage

A page opens a chapter when the title pattern appears within the first characters
of its text, and the title is the very start of the page text. A page can be
declared to open a chapter, or not to.

- **Where:** `ChapterSplitter.holds_new_chapter`, `get_chapter_name`,
  `extract_chapter_name`; page keys `type`, `chapter_info`, `no_new_chapter`.
- **Status:** declared (a pattern, a distance, and per-page declarations).
- **Proposal:** leave as data: it is the structure of the book.

#### IndentedLineStartsParagraph

Inside a page, a line starting with a given indentation (four spaces, according
to the documentation of `TextSanitizer`) starts a new paragraph.

- **Where:** the paragraph breaking pattern of the splitter of a book
  (`ParagraphAndBlockquoteSplitter`); the documentation of
  `TextSanitizer.normalize_newlines_and_multiple_whitespaces` states it.
- **Status:** declared, as a regular expression of the book.
- **Why it matters:** this is the rule `IndentedTailStartsParagraph`, applied
  inside a page and not across a page break. The merge across a page break
  ignores the indent that the same book uses inside the page, because the
  indent of the first line of a page is stripped (see
  `PageTextLeadingWhitespaceIsMargin`). The two belong together.
- **Proposal:** one rule (`IndentedLineStartsParagraph`), whose action sites
  are the paragraph breaking pattern and `ParagraphMerger._continues`.

#### PullQuoteIsRecognizedByItsIndentation, HeadingIsRecognizedByItsCentering

A pull quote is recognized by a deeper indentation, a heading by its centering
(patterns of the splitter of a book). A book that has them keeps the indent of
the first line of a page, to recognize them at the very top of it.

- **Where:** `ParagraphAndBlockquoteSplitter` (`blockquote_pattern`,
  `heading_pattern`) and the book override of
  `strip_page_text_leading_whitespace`.
- **Status:** declared, as patterns.
- **Proposal:** leave as patterns; mention them as the reason of the override.

#### RunningHeaderIsRemovedByPattern, KeyPointIsAPullQuote, DropCapIsRepaired

Each book may have a sanitizer (`StructuralInfoBase.sanitize_page_text`) that
removes the running header of a page, turns the key points set apart on a page
into pull quotes, or repairs the drop cap of an illuminated initial.

- **Where:** the book hooks. The package default does nothing.
- **Status:** declared, as code of the book.
- **Proposal:** a rule each (the belief is typographic), declared by the books
  that need it; the action site is the sanitizer, the trap is a page where the
  pattern finds nothing (or finds more than once).

### Declared by the book, as data

Not beliefs, so not rules: `typo_and_fix` (a regular expression and its fix, per
page), `dropped_sections` (titles), `table_declarations`, `table_row_continues`
(per page), `drop_page` (see `IllustrationRepeatingBodyIsDropped`),
`convert_to_logical_page_number` (the number printed on a page).

## Rejected as universal

- **A sentence is complete when it has a verb** (part of speech tagging).
  Rejected: the tagger misses the verb of an imperative sentence ("Seek
  forgiveness, and especially, forgive yourself.") and a footnote number after
  the punctuation made a complete sentence incomplete.
- **Monotone page markers prove the pages are right.** Rejected: markers can
  increase and still attribute a sentence to the wrong page (a heading ending a
  page was attributed to the next one).
- **A table lies on one page.** Rejected: in one converted book, 27 table rows
  were attributed to the wrong page. See `TableRowIsOnItsPrintedPage` in
  [rules_implicit.md](rules_implicit.md).

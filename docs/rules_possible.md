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

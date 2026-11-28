# Implicit rules

Design choices of pdf-to-markdown that hold for every book. A document never
declares them: they are always true. They are classes of
`pdf_to_markdown.typo_rules` (with `configurable = False`) so that the rules that
the code follows are all named, in one place, and can be discussed.

The rules that depend on the book are in
[rules_configurable.md](rules_configurable.md) and
[rules_possible.md](rules_possible.md).

## HeadingIsOnItsPrintedPage

A heading belongs to the page where the PDF prints it, never to the page of its
body. A reader who cites a heading must land on its exact page.

- **Met by the code:** yes. When the name of a level is the last line of a page,
  the level breaker carries it over to the next page to break the text it names
  (`LevelBreaker.break_into_sublevels`); the level is then given the page where
  its name is printed, and its text keeps the page it is printed on. A
  `Heading` (a sub-title that no level stands for) is created with the page of
  the text it was cut from, which is the page where it is printed.
- **Action site:** `LevelBreaker.break_into_sublevels` asks the rule
  (`HeadingIsOnItsPrintedPage.page_of_level`) for the page of the level; the rule
  comes from the rule register of the structural information.
- **Trap:** `HeadingIsOnItsPrintedPage.contradicted_by` warns when the level is
  not on the page of its name. It runs where the rule acts: it cannot see a
  heading that other code put on a wrong page (only the oracle can, partially).

## TableRowIsOnItsPrintedPage

Each row of a table belongs to the page where the PDF prints it.

- **Met by the code:** not yet. A `Table` carries a single page, so the rows of
  a table cut by a page break are attributed to the page where the table starts.
  Splitting a table per page is not planned yet.
- **Action site:** none, no code acts on it yet. The rule is registered and
  documented so that the gap is named; the test
  `tests/test_typo_rules_are_used.py` lists it as the one rule without an action
  site.

## Facts the code relies on

These are not rules: the converter is built on them.

- The output markdown carries no typography (no bold, no size, no superscript).
- A tab in the text of a page stands for a space (`TextExtractor.extract_all`).
- Curly quotes, the em dash (to "--"), the en dash (to "-") and the horizontal
  ellipsis (to "...") are folded to ASCII (`TextSanitizer.sanitize_characters`).
  The folding is many-to-one: the right single quotation mark is both a closing
  quote and an apostrophe, and cannot be told apart afterwards.
- A sentence belongs to the page where it starts.
- The blockquotes are ignored when looking for the first or last paragraph of a
  page: they are floating boxes, not part of the running text.

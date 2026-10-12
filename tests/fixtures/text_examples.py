# fmt: off
# All non-ASCII input characters are written as explicit Unicode escapes to
# prevent any editor or tool from silently converting them.

# Stage: chapter-name normalization
# Valid inputs: raw chapter titles as extracted from PDF pages.
# The [A-Z]\n[A-Z] collapse rule must NOT be applied at sentence level.
CHAPTER_NAME_EXAMPLES = [
    # (raw_name, expected_normalized)
    ("GET\nTING", "GETTING"),        # PDF-renderer mid-word uppercase split
    ("Chapter\nOne", "Chapter One"), # inter-word newline becomes space
    ("‘Quoted’", "'Quoted'"),  # U+2018/U+2019 folded to ASCII apostrophes
    ("ānanda", "ananda"),       # Pali macron-a (U+0101) folded to a
    ("dash — here", "dash -- here"),  # em dash folded to two hyphens
]

# Stage: character sanitization (sentence-level)
# Valid inputs: individual sentence text after NLTK tokenization.
# These examples must NOT be used to test chapter-level rules.
SENTENCE_CHARACTER_EXAMPLES = [
    # (input_text, expected_after_sanitize_characters)
    ("don’t",          "don't"),   # U+2019 RIGHT SINGLE QUOTATION MARK
    ("‘Hello’",   "'Hello'"), # U+2018/U+2019 pair
    ("“Hello”",   '"Hello"'), # U+201C/U+201D double quotes
    ("a — b",          "a -- b"),  # U+2014 EM DASH
    ("a – b",          "a - b"),   # U+2013 EN DASH
    ("end…",           "end..."),  # U+2026 HORIZONTAL ELLIPSIS
    ("ānanda",         "ananda"),  # Pali macron-a (U+0101)
    ("ṃetta",          "metta"),   # Pali m with dot below (U+1E43)
    ("☺",              ":-)"),     # U+263A WHITE SMILING FACE
]

# Stage: sentence splitting (paragraph -> sentences)
# split_paragraph_respecting_quotes is a passthrough: it returns its
# sanitized_sentences argument unchanged. Each entry is therefore a pair
# (paragraph_text, sanitized_sentences); the test asserts result == sanitized_sentences.
# paragraph_text is included to document the full call context even though the
# current implementation ignores it (it is part of the public API signature).
#
# Named codepoint constants used below to keep the intent visible without
# relying on an editor that may silently convert literal quote characters.
_apos = "\u0027"  # U+0027 ASCII APOSTROPHE
_lsqm = "\u2018"  # U+2018 LEFT SINGLE QUOTATION MARK
_rsqm = "\u2019"  # U+2019 RIGHT SINGLE QUOTATION MARK
SENTENCE_SPLIT_EXAMPLES = [
    # Multi-sentence paragraph enclosed in typographic single quotes.
    # Boundary apostrophes on each fragment are meaningful quotation-mark pieces.
    # Regression: quotes must not be stripped (old strip bug) nor re-wrapped
    # with spurious extra apostrophes (old re-wrap bug).
    (
        _lsqm + "It is overfull. No more will go in!" + _rsqm,
        [_apos + "It is overfull.", "No more will go in!" + _apos],
    ),
    # Single-sentence paragraph enclosed in typographic single quotes.
    (
        "‘A single sentence.’",
        ["'A single sentence.'"],
    ),
    # Unquoted paragraph: no apostrophes anywhere.
    (
        "Normal paragraph. Second sentence.",
        ["Normal paragraph.", "Second sentence."],
    ),
    # Mixed: quoted dialogue, attribution sentence, second quoted sentence.
    # Regression for spurious apostrophe injection: the attribution sentence
    # "Nan-in said." must NOT gain a trailing apostrophe.
    (
        "‘Like this cup,’ Nan-in said. ‘You are full of your own opinions.’",
        ["'Like this cup,' Nan-in said.", "'You are full of your own opinions.'"],
    ),
]
# fmt: on

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
# Each entry: (paragraph_text, pre-sanitized NLTK output, expected final sentences).
# The paragraph_text is used only for whole-paragraph-quote detection.
# The pre-sanitized sentences are what DocumentBuilder produces after
# sanitize_characters + _normalize_newlines_and_multiple_whitespaces per sentence.
SENTENCE_SPLIT_EXAMPLES = [
    # Multi-sentence quoted paragraph: each sentence gets re-wrapped in quotes.
    (
        "'It is overfull. No more will go in!'",
        ["'It is overfull.", "No more will go in!'"],
        ["'It is overfull.'", "'No more will go in!'"],
    ),
    # Single-sentence quoted paragraph: quotes preserved as-is (no strip).
    (
        "'A single sentence.'",
        ["'A single sentence.'"],
        ["'A single sentence.'"],
    ),
    # Unquoted paragraph: boundary apostrophes stripped (existing behavior).
    (
        "Normal paragraph. Second sentence.",
        ["Normal paragraph.", "Second sentence."],
        ["Normal paragraph.", "Second sentence."],
    ),
    # Unquoted paragraph with stray boundary apostrophe artifact.
    (
        "The monk said: it is good.",
        ["'The monk said:", "it is good.'"],
        ["The monk said:", "it is good."],
    ),
]
# fmt: on

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
# split_paragraph_respecting_quotes re-wraps sentence fragments that have an
# unbalanced boundary apostrophe. 
# Each entry of SENTENCE_SPLIT_EXAMPLES is a triple:
#   (paragraph_text, sanitized_sentences_in, expected_sentences_out)
# 
# sanitized_sentences_in is what NLTK tokenisation + sanitize_characters
# produces; expected_sentences_out is what split_paragraph_respecting_quotes
# must return.  The triple shape is required because the input and output are
# not identical: split_paragraph_respecting_quotes completes fragments that
# carry an unbalanced boundary apostrophe (a side-effect of NLTK splitting a
# singly-quoted paragraph), so a two-element (input, expected) pair is the
# minimum faithful representation of this transformation.
#
# Named codepoint constants used below to keep the intent visible without
# relying on an editor that may silently convert literal quote characters.
_apos = "\u0027"  # U+0027 ASCII APOSTROPHE
_lsqm = "\u2018"  # U+2018 LEFT SINGLE QUOTATION MARK
_rsqm = "\u2019"  # U+2019 RIGHT SINGLE QUOTATION MARK
SENTENCE_SPLIT_EXAMPLES = [
    # Multi-sentence paragraph enclosed in typographic single quotes.
    # NLTK attaches the opening quote to the first fragment and the closing
    # quote to the last. split_paragraph_respecting_quotes completes each
    # fragment with the missing paired apostrophe (odd-count rule).
    (
        _lsqm + "It is overfull. No more will go in!" + _rsqm,
        [_apos + "It is overfull.", "No more will go in!" + _apos],
        [_apos + "It is overfull." + _apos, _apos + "No more will go in!" + _apos],
    ),
    # Single-sentence paragraph enclosed in typographic single quotes.
    # The sentence already has balanced apostrophes (even count): no change.
    (
        "'A single sentence.'",
        ["'A single sentence.'"],
        ["'A single sentence.'"],
    ),
    # Unquoted paragraph: no apostrophes anywhere; no change.
    (
        "Normal paragraph. Second sentence.",
        ["Normal paragraph.", "Second sentence."],
        ["Normal paragraph.", "Second sentence."],
    ),
    # Mixed: quoted dialogue followed by attribution and a second quotation.
    # The attribution fragment "'Like this cup,' Nan-in said." has an even
    # apostrophe count (the pair 'Like...,' is balanced), so no apostrophe is
    # injected -- avoiding the spurious-apostrophe bug in earlier re-wrap
    # attempts.
    (
        "'Like this cup,' Nan-in said. 'You are full of your own opinions.'",
        ["'Like this cup,' Nan-in said.", "'You are full of your own opinions.'"],
        ["'Like this cup,' Nan-in said.", "'You are full of your own opinions.'"],
    ),
]
# fmt: on

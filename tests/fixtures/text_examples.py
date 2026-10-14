from pdf_to_markdown import TextSanitizer

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
# split_paragraph_respecting_quotes passes each sentence through unchanged.
# Each entry of SENTENCE_SPLIT_EXAMPLES is a triple:
#   (paragraph_text, sanitized_sentences_in, expected_sentences_out)
#  where
#    - paragraph_text: the original document text;
#    - sanitized_sentences_in: what NLTK tokenisation + sanitize_characters
#      produces; 
#    - expected_sentences_out: what split_paragraph_respecting_quotes
#      must return.  
# The triple shape is kept so that the test makes the passthrough contract
# explicit: 
#    expected_sentences_out == sanitized_sentences_in
# for every entry in this list.
#
# Named codepoint constants used below to keep the intent visible without
# relying on an editor that may silently convert literal quote characters.
_apos = "\u0027"  # U+0027 ASCII APOSTROPHE
_lsqm = "\u2018"  # U+2018 LEFT SINGLE QUOTATION MARK
_rsqm = "\u2019"  # U+2019 RIGHT SINGLE QUOTATION MARK
# All entries below are valid source text; split_paragraph_respecting_quotes
# passes them through unchanged.
SENTENCE_SPLIT_EXAMPLES = [
    # Multi-sentence paragraph enclosed in typographic single quotes.
    (
        _lsqm + "It is overfull. No more will go in!" + _rsqm,
        [_apos + "It is overfull.", "No more will go in!" + _apos],
        [_apos + "It is overfull.", "No more will go in!" + _apos],
    ),
    # Single-sentence paragraph enclosed in typographic single quotes.
    (
        "'A single sentence.'",
        ["'A single sentence.'"],
        ["'A single sentence.'"],
    ),
    # Unquoted paragraph.
    (
        "Normal paragraph. Second sentence.",
        ["Normal paragraph.", "Second sentence."],
        ["Normal paragraph.", "Second sentence."],
    ),
    # Quoted dialogue followed by attribution and a second quotation.
    (
        "'Like this cup,' Nan-in said. 'You are full of your own opinions.'",
        ["'Like this cup,' Nan-in said.", "'You are full of your own opinions.'"],
        ["'Like this cup,' Nan-in said.", "'You are full of your own opinions.'"],
    ),
    # Attribution sentence whose inner speech contains a possessive.
    (
        "He said: 'Ananda's path.'",
        ["He said: 'Ananda's path.'"],
        ["He said: 'Ananda's path.'"],
    ),
    # Sentences containing an inner balanced quotation ('homeless monk').
    # The word-terminal ' after monk is matched by the inner ' before homeless.
    # The second variant adds a leading contraction (I'm) which must not affect
    # the result: the sentence does not start with ' so no ambiguity arises.
    (
        "I am grateful to Nyogen Senzaki, 'homeless monk' exemplar-friend.",
        ["I am grateful to Nyogen Senzaki, 'homeless monk' exemplar-friend."],
        ["I am grateful to Nyogen Senzaki, 'homeless monk' exemplar-friend."],
    ),
    (
        "I'm grateful to Nyogen Senzaki, 'homeless monk' exemplar-friend.",
        ["I'm grateful to Nyogen Senzaki, 'homeless monk' exemplar-friend."],
        ["I'm grateful to Nyogen Senzaki, 'homeless monk' exemplar-friend."],
    ),
    # Singly-quoted paragraph where the first fragment contains a possessive.
    (
        _lsqm + "The monk's bowl was empty. Nothing remained." + _rsqm,
        [_apos + "The monk's bowl was empty.", "Nothing remained." + _apos],
        [_apos + "The monk's bowl was empty.", "Nothing remained." + _apos],
    ),
    # Singly-quoted paragraph where each fragment contains a contraction.
    (
        _lsqm + "It wasn't so. He didn't care." + _rsqm,
        [_apos + "It wasn't so.", "He didn't care." + _apos],
        [_apos + "It wasn't so.", "He didn't care." + _apos],
    ),
    # Dialogue attribution: the closing ' of 'You are dead all right' is a
    # word-terminal apostrophe after a common word (right). The attribution
    # tail 'observed the teacher.' has two words, distinguishing it from a
    # single-word possessive tail like "cat." — neither fragment is framed.
    # Source: Paul Reps, Zen Flesh Zen Bones (1957).
    (
        "'You are dead all right' observed the teacher. 'But how about that sound?'",
        [
            "'You are dead all right' observed the teacher.",
            "'But how about that sound?'",
        ],
        [
            "'You are dead all right' observed the teacher.",
            "'But how about that sound?'",
        ],
    ),
]

_ms = TextSanitizer._MISMATCH_START
_me = TextSanitizer._MISMATCH_END
SENTENCE_ERRONEOUS_QUOTES_EXAMPLES = [
    # Fragment starting with ' that contains no inner closing quote in the
    # [!?.,]' sense.  pdf_to_markdown cannot determine whether the word-
    # terminal apostrophe (James' before a space) is a possessive or a
    # closing quotation mark, so it frames the fragment.
    (
        "'John saw James' cat.",
        _ms + "'John saw James' cat." + _me,
    ),
]

# Sentences where the word-terminal ' closes a direct-speech quote opened
# at position 0; the attribution tail has >= 2 words, so the sentence passes
# through _frame_sentence_if_unbalanced unchanged.
SENTENCE_ATTRIBUTION_BOUNDARY_EXAMPLES = [
    # Exactly two attribution words ('he explained.') — the minimum tail
    # length that signals attribution rather than a single possessed noun.
    "'Everything in this life is impermanent' he explained.",
]
# fmt: on

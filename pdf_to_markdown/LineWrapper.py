import re


class LineWrapper:
    """Break the long line of a paragraph without ever starting a new paragraph.

    A single newline inside a markdown paragraph renders as a space, so the
    words are only separated by "\\n" (never by a blank line).
    """

    # A word that would open a block (list item, heading, blockquote) when it
    # is the first one of a line.
    _BLOCK_OPENING_WORD = re.compile(r"^(\d+[.)]|[-+*>]|#{1,6})$")

    # Stands for a space that must not be broken while wrapping.
    _UNBREAKABLE_SPACE = "\x00"

    @classmethod
    def wrap(
        cls,
        text: str,
        maximum_line_length: int | None,
        continuation_prefix: str = "",
    ) -> str:
        """Break text into lines of at most maximum_line_length characters.

        The text is expected to already start with the continuation prefix
        (indentation of a list item, "> " of a blockquote) when it has one.
        Each continuation line starts with that prefix, which counts in the
        line length. A word longer than the limit is left unbroken. None or a
        non positive limit leaves the text unchanged.
        """
        if not maximum_line_length or maximum_line_length <= 0:
            return text
        if len(text) <= maximum_line_length:
            return text
        first_line_prefix = (
            continuation_prefix if text.startswith(continuation_prefix) else ""
        )
        words = text[len(first_line_prefix) :].split(" ")
        lines: list[str] = []
        current_line = first_line_prefix
        line_has_word = False
        for word in words:
            if not line_has_word:
                current_line += word
                line_has_word = True
            elif len(current_line) + 1 + len(word) <= maximum_line_length or (
                cls._BLOCK_OPENING_WORD.match(word)
            ):
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = continuation_prefix + word
        lines.append(current_line)
        return "\n".join(lines)

    @classmethod
    def wrap_sentences(
        cls,
        sentences: list[str],
        maximum_line_length: int | None,
        line_prefix: str = "",
        suffix: str = "",
    ) -> str:
        """Break a paragraph at the end of sentences, into lines of at most
        maximum_line_length characters.

        Sentences are packed on a line while they fit. A sentence that does
        not fit even alone on a line is broken between words (see wrap). Every
        line starts with line_prefix (which counts in the line length) and the
        suffix is appended to the last line. None or a non positive limit
        gives a single line.
        """
        if not maximum_line_length or maximum_line_length <= 0:
            return line_prefix + " ".join(sentences) + suffix
        sentences = cls._join_sentences_inside_quotes(sentences)
        if suffix and sentences:
            # The suffix (e.g. an html comment) must neither start a line nor
            # be broken: it sticks to the last word of the last sentence.
            sentences = sentences[:-1] + [
                sentences[-1] + suffix.replace(" ", cls._UNBREAKABLE_SPACE)
            ]
        lines: list[str] = []
        current_line = ""
        for sentence in sentences:
            if current_line and (
                len(current_line) + 1 + len(sentence) <= maximum_line_length
            ):
                current_line += " " + sentence
                continue
            if current_line:
                lines.append(current_line)
            broken = cls.wrap(line_prefix + sentence, maximum_line_length, line_prefix)
            *complete_lines, current_line = broken.split("\n")
            lines.extend(complete_lines)
        lines.append(current_line)
        return "\n".join(lines).replace(cls._UNBREAKABLE_SPACE, " ")

    @staticmethod
    def _join_sentences_inside_quotes(sentences: list[str]) -> list[str]:
        """Glue the sentences that the splitter cut inside a double quote.

        A sentence ending with a question mark within a quotation ('"What is
        it?" he asked') is cut by the sentence splitter. A line must not be
        broken there: the sentences are joined as long as a double quote is
        left open (straight quotes are paired, curly ones are counted).
        """
        joined: list[str] = []
        quote_is_open = False
        for sentence in sentences:
            if quote_is_open:
                joined[-1] += " " + sentence
            else:
                joined.append(sentence)
            if sentence.count('"') % 2:
                quote_is_open = not quote_is_open
            elif sentence.count("\u201c") != sentence.count("\u201d"):
                quote_is_open = sentence.count("\u201c") > sentence.count("\u201d")
        return joined

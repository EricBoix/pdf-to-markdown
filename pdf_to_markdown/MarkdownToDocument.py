import json
import re
import nltk
import pypandoc
from mdutils.fileutils.fileutils import MarkDownFile

from pdf_to_markdown import (
    Document,
    TopLevelChapterOfParagraphs,
    PageLayout,
    Paragraph,
    BlockQuoteParagraph,
    Sentence,
)


class MarkdownToDocument:
    """Read a markdown file and reconstruct a pdf_to_markdown Document from it.

    Strategy: rather than parsing markdown with a hand-written regex scanner,
    we delegate to pandoc (via pypandoc) which converts the source file into a
    language-agnostic JSON AST.  Walking that AST is reliable and handles
    edge-cases (nested quotes, footnotes, links, blockquotes, HTML comments)
    that regex approaches miss.

    The AST is a tree of typed nodes.  Block-level nodes (Header, Para,
    BlockQuote, RawBlock) drive the Document/Chapter/Paragraph hierarchy.
    Inline-level nodes (Str, Space, Quoted, Link, Note, ...) are flattened
    to plain text by _extract_text, which recurses as needed.

    Two concerns require extra bookkeeping beyond the basic walk:
    - Footnotes: pandoc inlines every [^name] reference at its call site as an
      anonymous Note node, discarding the label.  _footnote_reference_order
      recovers the original names from the raw source so they can be
      reattached, and duplicate references to the same footnote are collapsed
      to a single definition.
    - Omitted sections: headers carrying the HTML comment _OMIT_MARKER (and
      all content beneath them) are silently skipped.
    """
    # Note: concerning the JSON AST delivered by pandoc, many thanks to
    https://stackoverflow.com/questions/40945364/parsing-elements-from-a-markdown-file-in-python-3)

    _DUMMY_LAYOUT = PageLayout(reader_page_number=0, page_number=0)
    _OMIT_MARKER = "<!-- omit from pdf-to-markdown:"
    _QUOTE_CHARS = {"DoubleQuote": ('"', '"'), "SingleQuote": ("'", "'")}

    def __init__(self, filepath: str) -> None:
        self._filepath = filepath

    def get_document(self) -> Document:
        # markdown-smart disables pandoc's smart-quotes extension so ASCII
        # ' and " are not converted to typographic equivalents in the AST.
        blocks = json.loads(
            pypandoc.convert_file(self._filepath, "json", format="markdown-smart")
        )["blocks"]

        document: Document | None = None
        current_chapter: TopLevelChapterOfParagraphs | None = None
        omit_next_header = False
        omitted_level: int | None = None
        fn_state: dict = {
            "names": self._footnote_reference_order(self._filepath),
            "seen": {},
            "definitions": [],
        }

        def flush_paragraph(text: str, blockquote: bool = False) -> None:
            # Split text into sentences, merge stray footnote refs, and
            # append the result as a Paragraph (or BlockQuoteParagraph).
            if not text or current_chapter is None:
                return
            paragraph = (BlockQuoteParagraph if blockquote else Paragraph)(
                self._DUMMY_LAYOUT
            )
            for sent_text in self._merge_footnote_refs(nltk.sent_tokenize(text)):
                paragraph.add_sublevel(Sentence(sent_text, self._DUMMY_LAYOUT))
            paragraph.renumber_sublevels()
            current_chapter.add_sublevel(paragraph)

        def dispatch_block(block: dict) -> None:
            # Route one pandoc block to the appropriate handler, maintaining
            # the omit-section state and building document/current_chapter
            # incrementally.
            nonlocal document, current_chapter, omit_next_header, omitted_level
            t = block["t"]
            if (
                t == "RawBlock"
                and block["c"][0] == "html"
                and self._OMIT_MARKER in block["c"][1]
            ):
                omit_next_header = True
                return
            if t == "Header":
                level, _attrs, inlines = block["c"]
                if omitted_level is not None and level <= omitted_level:
                    omitted_level = None
                if omit_next_header or self._has_omit_marker(inlines):
                    omitted_level = level
                    omit_next_header = False
                    return
                title = self._extract_text(inlines, fn_state)
                if level == 1:
                    document = Document(title)
                elif level == 2:
                    if current_chapter is not None:
                        current_chapter.renumber_sublevels()
                        document.add_chapter(current_chapter)
                    current_chapter = TopLevelChapterOfParagraphs(title)
                return
            if omitted_level is not None:
                return
            if t == "Para":
                flush_paragraph(self._extract_text(block["c"], fn_state))
            elif t == "BlockQuote":
                for inner in block["c"]:
                    if inner["t"] == "Para":
                        flush_paragraph(
                            self._extract_text(inner["c"], fn_state), blockquote=True
                        )

        for block in blocks:
            dispatch_block(block)

        if current_chapter is not None:
            current_chapter.renumber_sublevels()
            document.add_chapter(current_chapter)

        if fn_state["definitions"] and current_chapter is not None:
            for name, content in fn_state["definitions"]:
                paragraph = Paragraph(self._DUMMY_LAYOUT)
                paragraph.add_sublevel(
                    Sentence(f"[^{name}]: {content}", self._DUMMY_LAYOUT)
                )
                paragraph.renumber_sublevels()
                current_chapter.add_sublevel(paragraph)
            current_chapter.renumber_sublevels()

        if document is not None:
            document.renumber_sublevels()

        return document

    @staticmethod
    def _footnote_reference_order(filepath: str) -> list[str]:
        # Pandoc anonymizes footnote names: every [^name] in the source
        # becomes a bare Note inline element in the AST with no label.
        # We recover the original names by scanning the raw source for
        # [^name] references (excluding definition lines [^name]:) in
        # first-appearance order, then positionally match them to the
        # Note elements the AST emits in the same order.
        content = MarkDownFile.read_file(filepath)
        seen: set[str] = set()
        ordered: list[str] = []
        for name in re.findall(r"\[\^([^\]]+)\](?!:)", content):
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    @staticmethod
    def _extract_text(inlines: list, fn_state: dict | None = None) -> str:
        """Recursively extract plain text from a pandoc inline list.

        fn_state (optional) is a mutable dict that tracks footnotes across the
        whole document:
            "names"       - unique footnote names in source order, recovered by
                            _footnote_reference_order (pandoc drops them from the AST)
            "seen"        - maps note content -> original name; a footnote referenced
                            N times produces N identical Note elements in the AST, so
                            we deduplicate by content and emit only one definition
            "definitions" - ordered (name, content) pairs for first occurrences only,
                            written as [^name]: ... paragraphs at the end of the document
        """
        parts = []
        for inline in inlines:
            t = inline["t"]
            if t == "Str":
                parts.append(inline["c"])
            elif t in ("Space", "SoftBreak", "LineBreak"):
                parts.append(" ")
            elif t == "Quoted":
                quote_type = inline["c"][0]["t"]
                open_q, close_q = MarkdownToDocument._QUOTE_CHARS.get(
                    quote_type, ('"', '"')
                )
                parts.append(
                    open_q
                    + MarkdownToDocument._extract_text(inline["c"][1], fn_state)
                    + close_q
                )
            elif t == "Link":
                # Reconstruct markdown link syntax so the URL survives
                # the round-trip.
                _attrs, link_inlines, (url, _title) = inline["c"]
                link_text = MarkdownToDocument._extract_text(link_inlines, fn_state)
                parts.append(f"[{link_text}]({url})")
            elif t == "Note" and fn_state is not None:
                note_parts = [
                    MarkdownToDocument._extract_text(block["c"], fn_state)
                    for block in inline["c"]
                    if block["t"] == "Para"
                ]
                content = " ".join(note_parts)
                if content in fn_state["seen"]:
                    # Duplicate reference: reuse the existing name,
                    # do not add a new definition entry.
                    name = fn_state["seen"][content]
                else:
                    idx = len(fn_state["definitions"])
                    names = fn_state["names"]
                    name = names[idx] if idx < len(names) else f"note_{idx + 1}"
                    fn_state["seen"][content] = name
                    fn_state["definitions"].append((name, content))
                parts.append(f"[^{name}]")
        return "".join(parts).strip()

    @staticmethod
    def _merge_footnote_refs(sentences: list[str]) -> list[str]:
        # nltk splits "text.[^name]" at the period, leaving "[^name]"
        # as a spurious sentence. Reattach any fragment that is nothing
        # but footnote references to the preceding sentence without
        # adding a space.
        footnote_ref_only = re.compile(r"^\s*(\[\^[^\]]+\]\s*)+$")
        merged: list[str] = []
        for sent in sentences:
            if footnote_ref_only.match(sent) and merged:
                merged[-1] += sent.strip()
            else:
                merged.append(sent)
        return merged

    @staticmethod
    def _has_omit_marker(inlines: list) -> bool:
        return any(
            inline["t"] == "RawInline"
            and inline["c"][0] == "html"
            and MarkdownToDocument._OMIT_MARKER in inline["c"][1]
            for inline in inlines
        )

import sys
import json
from .Model import (
    TopLevelChapterOfParagraphs,
    SubChapterOfParagraphs,
    Paragraph,
    Sentence,
)

# Warning: implicit dependency towards LangChain's Document class


def _sentence_metadata(obj: Sentence) -> dict:
    root = obj.hierarchical_toplevel
    pub = root.publication_info if root else None

    paragraph = obj.owning_hierarchical_level
    level = paragraph.owning_hierarchical_level if paragraph else None

    if isinstance(level, SubChapterOfParagraphs):
        super_chapter = level.owning_hierarchical_level
        chapter_name = super_chapter.name if super_chapter else None
        chapter_number = super_chapter.number if super_chapter else None
        subchapter_name = level.name
        subchapter_number = level.number
    else:
        chapter_name = level.name if level else None
        chapter_number = level.number if level else None
        subchapter_name = None
        subchapter_number = None

    return {
        "doc_name": pub.doc_name if pub else None,
        "doc_title": root.title if root else None,
        "author": pub.author if pub else None,
        "isbn": pub.isbn if pub else None,
        "chapter": chapter_name,
        "chapter_number": chapter_number,
        "subchapter": subchapter_name,
        "subchapter_number": subchapter_number,
        "paragraph_number": paragraph.number if paragraph else None,
        "sentence_number": obj.number,
        "page": obj.page_layout.reader_page_number if obj.page_layout else None,
    }


class LangChainDocumentEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Sentence):
            return {
                "__document__": True,
                "metadata": _sentence_metadata(obj),
                "page_content": obj.text,
            }
        # Let the base class default method raise the TypeError
        return super().default(obj)


class WriteAsLangchainDocuments:
    """
    Export the ConvertPdfToMarkdown Document transposed to Langchain's Document objects and into JSON based files
    References: https://reference.langchain.com/python/langchain-core/documents/base/Document
    """

    def __init__(self, document):
        self._document = document

    def _collect_level_sentences(self, level, output_json_file):
        collected_sentences = []
        for sublevel in level.get_sublevels():
            if isinstance(sublevel, Paragraph):
                sentences = sublevel.get_sentences()
                if not sentences:
                    continue
                for sentence in sentences:
                    collected_sentences.append(sentence)
                continue
            elif isinstance(
                sublevel, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
            ):
                collected_sentences.extend(
                    self._collect_level_sentences(sublevel, output_json_file)
                )
                continue
            else:
                print("Level ", sublevel, "not serializable as sentences ???")
                print("Exiting.")
                sys.exit()
        return collected_sentences

    def write_sentences(self, output_json_filename):
        with open(output_json_filename, "w+") as output_json_file:
            collected_sentences = []
            for chapter in self._document.get_chapters():
                collected_sentences.extend(
                    self._collect_level_sentences(chapter, output_json_file)
                )
            json.dump(
                collected_sentences,
                cls=LangChainDocumentEncoder,
                fp=output_json_file,
                indent=4,
            )

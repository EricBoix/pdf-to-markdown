import pypdf
from .Errors import ConverterError
from .Model import (
    TopLevelChapterOfParagraphs,
    SubChapterOfParagraphs,
    SuperChapter,
    Paragraph,
)

# A set of debugging utilities.


def print_document_raw_pages(pdf_filename) -> None:
    """
    Print the pages of the document.
    """
    reader = pypdf.PdfReader(pdf_filename)

    print("##########################################################")
    print("##########################################################")
    print("##### RAW DOCUMENT WITH A PAGE BASED BREAKDOWN ###########")
    print("##########################################################")
    print("##########################################################\n")
    print("Total number of pages: ", len(reader.pages))

    for page_number in range(len(reader.pages)):
        page = reader.pages[page_number]
        print("############### Page number ", page_number, "############")
        print(repr(page.extract_text(extraction_mode="layout")))

    print("##########################################################")
    print("################## END OF RAW DOCUMENT ###################")
    print("##########################################################\n")


class PrintDocument:
    def __init__(self, document) -> None:
        self._document = document

    def pages(self) -> None:
        print("##########################################################")
        print("##########################################################")
        print("############ DOCUMENT AS SET OF PAGES ####################")
        print("##########################################################")
        print("##########################################################\n")
        for chapter in self._document.get_chapters():
            print("#################################")
            print("################## Chapter name: ", chapter.name)
            print("#################################")
            for page in chapter.pages:
                print("################# Page content:")
                print(repr(page))
                print("")

    def paragraphs(self) -> None:
        print("##########################################################")
        print("##########################################################")
        print("############ DOCUMENT AS SET OF PARAGRAPHS ###############")
        print("##########################################################")
        print("##########################################################\n")
        for chapter in self._document.get_chapters():
            print("###################################################################")
            print("################## Chapter name: ", chapter.name)
            print("###################################################################")
            for paragraph in chapter.get_sublevels():
                print(
                    "Paragraph (ref:",
                    paragraph.get_document_reference_long(),
                    "):\n",
                    paragraph.text,
                    "\n",
                )

    def sentences(self) -> None:
        print("##########################################################")
        print("##########################################################")
        print("##### DOCUMENT AS SET OF SENTENCES WITHIN PARAGRAPHS #####")
        print("##########################################################")
        print("##########################################################\n")
        for chapter in self._document.get_chapters():
            self._print_chapter(chapter)

    def with_subchapter_sentences(self) -> None:
        print("##########################################################")
        print("##########################################################")
        print("############### DOCUMENT DOWN TO THE SENTENCES ###########")
        print("##########################################################")
        print("##########################################################\n")
        for superchapter in self._document.get_chapters():
            print("###################################################################")
            print("################## Super Chapter name: ", superchapter.name)
            print("###################################################################")
            for sublevel in superchapter.get_sublevels():
                if isinstance(
                    sublevel, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
                ):
                    self._print_chapter(sublevel)
                elif isinstance(sublevel, Paragraph):
                    self._print_paragraph_and_sentences(sublevel)

    def _print_chapter(self, chapter) -> None:
        if isinstance(chapter, SuperChapter):
            self._print_super_chapter(chapter)
            return
        if isinstance(chapter, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)):
            self._print_chapter_of_paragraphs(chapter)

    def _print_super_chapter(self, super_chapter) -> None:
        if not isinstance(super_chapter, SuperChapter):
            raise ConverterError(
                f"Chapter {super_chapter.name} is not a SuperChapter."
            )
        print("###################################################################")
        print("################## Super Chapter name: ", super_chapter.name)
        print("###################################################################")
        for sublevel in super_chapter.get_sublevels():
            if isinstance(
                sublevel, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
            ):
                self._print_chapter_of_paragraphs(sublevel)
                continue
            if isinstance(sublevel, Paragraph):
                self._print_paragraph_and_sentences(sublevel)
                continue
            raise ConverterError(
                f"Chapter {super_chapter.name} sublevel is of unknown type."
            )

    def _print_chapter_of_paragraphs(self, chapter) -> None:
        if not isinstance(
            chapter, (TopLevelChapterOfParagraphs, SubChapterOfParagraphs)
        ):
            raise ConverterError(
                f"Chapter {chapter.name} is not a ChapterOfParagraphs."
            )
        print("###################################################################")
        print("################## Chapter name: ", chapter.name)
        print("###################################################################")
        for paragraph in chapter.get_sublevels():
            self._print_paragraph_and_sentences(paragraph)

    def _print_paragraph_and_sentences(self, paragraph) -> None:
        print("###", paragraph.get_document_reference_long())
        sentences = paragraph.get_sentences()
        if not sentences:
            print("PARAGRAPH IS EMPTY OF SENTENCES")
            return
        for sentence in sentences:
            print(
                f"{sentence.text} \n   [Reference: {sentence.get_document_reference_long()}]"
            )

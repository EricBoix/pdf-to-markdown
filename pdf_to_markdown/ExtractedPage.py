class ExtractedPage:
    """
    Representation of a pdf extracted page.

    Attributes
    ----------
    page_number: int
        The index of the page as it appears extracted by pydf::PdfReader()
    original_pdf_page: str
        The text as originally extracted by the constructor caller
    removed_first_line_indentation: int
        The number of whitespaces that the extraction removed from the
        indentation of the first line of the page text. A table starting at
        the very top of a page needs them back in order to align its first
        line with the other ones.

    Note: Chapter detection and extraction is handled by chapter_splitter
    classes defined in each book's StructuralInfo.
    """

    def __init__(self, page_number, layout, original_page):
        self.page_number = page_number
        self.page_layout = layout
        self.original_pdf_page = original_page
        self.text = None
        self.removed_first_line_indentation = 0

    def set_text(self, text_in) -> None:
        self.text = text_in

    def __repr__(self) -> str:
        return (
            "Extracted paragraph id: " + repr(id(self)) + "\n"
            "Python page number: " + str(self.page_number) + "\n"
            "Reader page number (written on paper and/or as given by pdf viewer): "
            + repr(self.page_layout.reader_page_number)
            + "\n"
            + "Extracted text: "
            + repr(self.text)
        )

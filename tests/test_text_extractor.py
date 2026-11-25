"""Tests for the text-extraction pipeline stage.

TextExtractor reads text from pypdf page objects. These tests mock pypdf to
verify the normalization rules (tab→space, lstrip) without needing a real PDF.
"""

from unittest.mock import MagicMock

from pdf_to_markdown import TextExtractor


def _make_mock(page_texts: list[str]):
    """Build a mock reader and structural_info for the given page texts."""
    mock_pages = []
    for text in page_texts:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)

    mock_reader = MagicMock()
    mock_reader.pages = mock_pages

    mock_si = MagicMock()
    mock_si.total_page_number = len(page_texts)
    mock_si._page_is_dropped.return_value = False
    mock_si.strip_page_text_leading_whitespace.side_effect = (
        lambda page_text: page_text.lstrip()
    )

    return mock_reader, mock_si


def test_extract_all_tabs_become_spaces():
    reader, si = _make_mock(["Hello\tworld"])
    result = TextExtractor(reader, si).extract_all()
    assert result == {0: "Hello world"}


def test_extract_all_leading_whitespace_stripped():
    reader, si = _make_mock(["   text content"])
    result = TextExtractor(reader, si).extract_all()
    assert result == {0: "text content"}


def test_extract_all_multiple_pages_keyed_by_index():
    reader, si = _make_mock(["Page zero.", "Page one."])
    result = TextExtractor(reader, si).extract_all()
    assert result[0] == "Page zero."
    assert result[1] == "Page one."


def test_extract_all_dropped_page_skipped():
    reader, si = _make_mock(["Kept.", "Dropped.", "Kept."])
    # Mark page 1 as dropped.
    si._page_is_dropped.side_effect = lambda page_number: page_number == 1
    result = TextExtractor(reader, si).extract_all()
    assert 1 not in result
    assert 0 in result
    assert 2 in result


def test_extract_all_layout_mode_fallback():
    # When layout mode raises NotImplementedError, standard extraction is used.
    page = MagicMock()
    page.extract_text.side_effect = [NotImplementedError(), "fallback text"]

    mock_reader = MagicMock()
    mock_reader.pages = [page]

    mock_si = MagicMock()
    mock_si.total_page_number = 1
    mock_si._page_is_dropped.return_value = False
    mock_si.strip_page_text_leading_whitespace.side_effect = (
        lambda page_text: page_text.lstrip()
    )

    result = TextExtractor(mock_reader, mock_si).extract_all()
    assert result == {0: "fallback text"}


def test_extract_all_text_is_folded_to_ascii():
    reader, si = _make_mock(["He said “No.” It’s — Paññā – done…"])
    result = TextExtractor(reader, si).extract_all()
    assert result == {0: 'He said "No." It\'s -- Panna - done...'}
    assert result[0].isascii()


def test_extract_all_spaced_ellipsis_is_spelled_plainly():
    reader, si = _make_mock(["there is . . . and no space before. . . either"])
    result = TextExtractor(reader, si).extract_all()
    assert result == {0: "there is... and no space before... either"}


def test_extract_all_folds_before_the_leading_whitespace_is_stripped():
    # The book decides what to strip once it sees plain ASCII text.
    reader, si = _make_mock(["   “quoted”"])
    TextExtractor(reader, si).extract_all()
    si.strip_page_text_leading_whitespace.assert_called_once_with('   "quoted"')

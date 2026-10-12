"""Generate minimal fixture PDFs for pipeline tests using fpdf2."""

from fpdf import FPDF


def make_fixture_pdf(path: str) -> None:
    """Write a 4-page PDF that exercises all pipeline-stage contexts.

    Page layout:
        0 — Chapter One heading (chapter-name context)
        1 — Quoted multi-sentence body (sentence-split context)
        2 — Chapter Two heading (chapter-name context, Pali-free for simplicity)
        3 — Plain body sentence (baseline)
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    # Page 0: chapter heading only — no body text
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(text="Chapter One")

    # Page 1: quoted multi-sentence paragraph
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="'It is overfull. No more will go in!'")

    # Page 2: chapter heading only
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(text="Chapter Two")

    # Page 3: plain paragraph
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Correct sentences are valuable.")

    pdf.output(str(path))

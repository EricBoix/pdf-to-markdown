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


def make_superchapter_fixture_pdf(path: str) -> None:
    """Write a 5-page PDF whose chapters are split into numbered sub-chapters.

    Page layout:
        0 — "Part One" heading (super chapter)
        1 — sub-chapter "1. Alpha" with a two-sentence body
        2 — sub-chapter "2. Beta" with a one-sentence body
        3 — "Part Two" heading (super chapter)
        4 — sub-chapter "3. Gamma" with a one-sentence body
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    def add_heading_page(heading: str) -> None:
        pdf.add_page()
        pdf.set_font("Helvetica", size=14)
        pdf.cell(text=heading)

    def add_sub_chapter_page(sub_chapter_title: str, body: str) -> None:
        pdf.add_page()
        pdf.set_font("Helvetica", size=14)
        pdf.cell(text=sub_chapter_title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)
        pdf.set_font("Helvetica", size=12)
        pdf.cell(text=body)

    add_heading_page("Part One")
    add_sub_chapter_page("1. Alpha", "First alpha sentence. Second alpha sentence.")
    add_sub_chapter_page("2. Beta", "Beta sentence.")
    add_heading_page("Part Two")
    add_sub_chapter_page("3. Gamma", "Gamma sentence.")

    pdf.output(str(path))

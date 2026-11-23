"""Generate synthetic applicant PDFs that exercise known extraction pitfalls.

Run with PyMuPDF installed: python make_fixtures.py
The expected results for each file live in expected.json next to this script.
"""

from pathlib import Path

import fitz

HERE = Path(__file__).parent
# Base-14 fonts can't encode U+2010, so typographic hyphens need an embedded font.
UNICODE_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FILLER = ["Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod"] * 5


def write_page(
    doc: fitz.Document, lines: list[str], links: list[tuple[str, str]] = (), fontfile: str | None = None
) -> None:
    page = doc.new_page()
    y = 72
    # insert_text limits fonts to a one-byte encoding; TextWriter writes full Unicode.
    writer = fitz.TextWriter(page.rect)
    font = fitz.Font(fontfile=fontfile) if fontfile else fitz.Font("helv")
    for line in lines:
        writer.append((72, y), line, font=font, fontsize=10)
        y += 14
    writer.write_text(page)
    for i, (label, uri) in enumerate(links):
        top = 600 + i * 20
        page.insert_text((72, top + 12), label, fontsize=10)
        page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(72, top, 300, top + 15), "uri": uri})


def single(name: str, lines: list[str], links: list[tuple[str, str]] = (), fontfile: str | None = None) -> None:
    doc = fitz.open()
    write_page(doc, lines + FILLER, links, fontfile)
    # Embedding only the used glyphs keeps the file small.
    doc.subset_fonts()
    doc.save(HERE / name)


def bundle_with_reference_letter() -> None:
    doc = fitz.open()
    write_page(doc, ["Curriculum Vitae", "Hana Ito", "ORCID: 0000-0001-5109-3700", "Email: hana.ito@example.org"] + FILLER)
    write_page(
        doc,
        [
            "Publications",
            "1. H. Ito, K. Tanaka (ORCID 0000-0003-1415-9269). A study of things. J. Stuff 2024.",
        ]
        + FILLER,
    )
    write_page(
        doc,
        [
            "Dear Members of the Selection Committee,",
            "I am pleased to recommend Hana Ito for the PhD position in your group.",
            "Prof. Dr. Ref Erence, ORCID: 0000-0002-1825-0097",
            "https://scholar.google.com/citations?user=RefRefRefRef",
            "Sincerely,",
        ]
        + FILLER,
    )
    doc.save(HERE / "11_bundle_with_reference.pdf")


def scanned() -> None:
    text_doc = fitz.open()
    write_page(text_doc, ["Scanned CV", "ORCID: 0000-0002-1825-0097"] + FILLER)
    # A small grey JPEG keeps the fixture light; only the absence of text matters.
    pixmap = text_doc[0].get_pixmap(dpi=72, colorspace=fitz.csGRAY)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(page.rect, stream=pixmap.tobytes("jpeg", jpg_quality=60))
    doc.save(HERE / "12_scanned.pdf")


def main() -> None:
    single("01_plain.pdf", ["Jane Doe", "ORCID: 0000-0002-1825-0097", "https://scholar.google.com/citations?user=AbCdEfGhIjKl"])
    single("02_unicode_hyphen.pdf", ["John Roe", "ORCID: 0000‐0002‐1825‐0097"])
    single(
        "03_linebreak.pdf",
        ["Ann Poe", "ORCID https://orcid.org/0000-0002-", "1825-0097", "Scholar: https://scholar.google.com/citations?", "user=AbCdEfGhIjKl&hl=en"],
    )
    single("04_hl_first.pdf", ["Bo Li", "https://scholar.google.de/citations?hl=de&user=AbCdEfGhIjKl"])
    single(
        "05_same_profile_twice.pdf",
        ["Cy Ho", "https://scholar.google.com/citations?user=AbCdEfGhIjKl&hl=en", "https://scholar.google.com/citations?user=AbCdEfGhIjKl"],
    )
    single("06_bad_checksum.pdf", ["Phone 1234-5678-9012-3456 (office)"])
    single(
        "07_coauthors.pdf",
        [
            "Dee Ka, ORCID 0000-0002-1825-0097",
            "Supervisor ORCID 0000-0001-5109-3700",
            "Co-author ORCID 0000-0003-1415-9269",
            "https://scholar.google.com/citations?user=AbCdEfGhIjKl",
        ],
    )
    single(
        "08_link_only.pdf",
        ["Eve Fa"],
        [("My ORCID", "https://orcid.org/0000-0002-1825-0097"), ("Scholar", "https://scholar.google.com/citations?user=AbCdEfGhIjKl")],
    )
    single("09_UPPER.PDF", ["Fay Go", "ORCID: 0000-0002-1825-0097"])
    single("10_hl_only.pdf", ["Gil Hu", "https://scholar.google.com/citations?hl=en"])
    bundle_with_reference_letter()
    scanned()
    single("13_x_checksum.pdf", ["Ida Ju", "ORCID iD: 0000-0002-1000-000X"])
    single("14_uk_amp.pdf", ["Jo Ki", "Google Scholar: https://scholar.google.co.uk/citations?user=AbCdEfGhIjKl&amp;hl=en"])
    # Word's autocorrect turns hyphens typed between digits into en dashes.
    single("16_en_dash.pdf", ["Kay Lo", "ORCID: 0000\u20130002\u20131825\u20130097"])
    (HERE / "15_corrupt.pdf").write_bytes(b"%PDF-1.7\nthis is not really a pdf\n")


if __name__ == "__main__":
    main()

from functools import lru_cache
from html import escape
from io import BytesIO
from pathlib import Path
from unicodedata import category

from django.conf import settings
from PIL import Image as PillowImage
from PIL import ImageDraw, ImageFont, features
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .common import pdf_response, table_contributor_lines
from .tabular import created_label, grouped_books

FONT_PIXELS = 36
IMAGE_SCALE = 4
COLUMN_WIDTHS = (22, 58, 53, 37, 62, 43)


def bundled_font_path():
    return Path(settings.BASE_DIR) / (
        "apps/ingestion/pipeline/epub_properties/fonts/NotoSansBengali-Regular.ttf"
    )


@lru_cache(maxsize=2)
def text_fonts(font_path):
    return (
        ImageFont.truetype(
            str(font_path), FONT_PIXELS, layout_engine=ImageFont.Layout.RAQM
        ),
        ImageFont.load_default(size=FONT_PIXELS),
    )


def script_runs(text):
    runs: list[tuple[int, str]] = []
    for character in text:
        script = (
            0 if "\u0980" <= character <= "\u09ff" or character in "\u200c\u200d" else 1
        )
        if runs and runs[-1][0] == script:
            runs[-1] = script, runs[-1][1] + character
        else:
            runs.append((script, character))
    return runs


def text_width(text, fonts):
    return sum(fonts[script].getlength(run) for script, run in script_runs(text))


def word_clusters(word):
    clusters: list[str] = []
    for character in word:
        attached = category(character).startswith("M") or character in "\u200c\u200d"
        if clusters and (attached or clusters[-1].endswith(("\u09cd", "\u200d"))):
            clusters[-1] += character
        else:
            clusters.append(character)
    return clusters


def word_parts(word, fonts, width):
    parts, part = [], ""
    for cluster in word_clusters(word):
        if part and text_width(part + cluster, fonts) > width:
            parts.append(part)
            part = cluster
        else:
            part += cluster
    return [*parts, part]


def wrap_words(text, fonts, width):
    lines = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        words = [
            part
            for word in paragraph.split()
            for part in word_parts(word, fonts, width)
        ]
        for word in words:
            candidate = f"{line} {word}".strip()
            if line and text_width(candidate, fonts) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def shaped_cell(text, width):
    font_path = settings.CATALOG_EXPORT_FONT_PATH or bundled_font_path()
    if not Path(font_path).is_file():
        raise RuntimeError(
            "PDF text font is missing. Restore the bundled Bengali font."
        )
    fonts = text_fonts(str(font_path))
    pixel_width = max(1, int((width * mm - 12) * IMAGE_SCALE))
    lines = wrap_words(text, fonts, pixel_width)
    line_height = FONT_PIXELS * 2
    image = PillowImage.new(
        "RGB", (pixel_width, max(1, len(lines) * line_height)), "white"
    )
    drawing = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        horizontal = 0.0
        for script, run in script_runs(line):
            drawing.text(
                (horizontal, index * line_height + FONT_PIXELS * 1.4),
                run,
                font=fonts[script],
                fill="#17251f",
                anchor="ls",
            )
            horizontal += fonts[script].getlength(run)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return Image(
        buffer, width=pixel_width / IMAGE_SCALE, height=image.height / IMAGE_SCALE
    )


def pdf_cell(text, width):
    if any("\u0980" <= character <= "\u09ff" for character in text):
        if not features.check_feature("raqm"):
            raise RuntimeError(
                "Bengali PDF export requires Pillow with RAQM text shaping. "
                "Use the supplied API image, which includes the required text libraries."
            )
        return shaped_cell(text, width)
    style = ParagraphStyle("ExportBody", fontName="Helvetica", fontSize=9, leading=13)
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def book_cells(book):
    categories = ", ".join(
        relation.category.name for relation in book.book_categories.all()
    )
    details = [
        book.publisher,
    ]
    details.extend(relation.series.name for relation in book.book_series.all())
    details.extend([book.language, "Compilation" if book.is_compilation else ""])
    return (
        book.catalog_code or "",
        book.title,
        "\n".join(table_contributor_lines(book)),
        categories,
        "\n".join(filter(None, details)),
        created_label(book),
    )


def book_table(books):
    headers = (
        "Book ID",
        "Title",
        "Contributors",
        "Categories",
        "Details",
        "Created (Dhaka)",
    )
    rows = [
        [
            pdf_cell(text, width)
            for text, width in zip(headers, COLUMN_WIDTHS, strict=True)
        ]
    ]
    rows.extend(
        [
            pdf_cell(text, width)
            for text, width in zip(book_cells(book), COLUMN_WIDTHS, strict=True)
        ]
        for book in books
    )
    table = Table(
        rows,
        colWidths=[width * mm for width in COLUMN_WIDTHS],
        repeatRows=1,
        splitInRow=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcece3")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9baea3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_grouped_pdf_response(books, grouping):
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Books" if grouping else "Book List",
    )
    story = []
    for label, entries in grouped_books(books, grouping):
        story.extend(
            [
                pdf_cell(label if grouping else "Book List", 275),
                Spacer(1, 4 * mm),
                book_table(entries),
                Spacer(1, 5 * mm),
            ]
        )
    document.build(story)
    return pdf_response("book-list.pdf", output.getvalue())

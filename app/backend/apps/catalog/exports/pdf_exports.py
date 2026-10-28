from io import BytesIO

from .common import (
    book_export_filename,
    identity_ticket_contributor_line,
    pdf_response,
    resolve_pdf_font,
)


def make_book_list_pdf(books):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Spacer

    from .grouped_pdf import book_table, pdf_cell

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    document.build([pdf_cell("Book List", 275), Spacer(1, 6 * mm), book_table(books)])
    return buffer.getvalue()


def make_book_tickets_pdf(books):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError("PDF export requires reportlab to be installed.") from exc

    font_name = resolve_pdf_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CatalogTicketTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=14,
        leading=18,
    )
    ticket_style = ParagraphStyle(
        "CatalogTicketBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8,
        leading=10,
    )

    cells = []
    row: list[Paragraph | str] = []
    for book in books:
        ticket_html = f"<b>{__import__('html').escape(book.catalog_code or '')}</b><br/>{__import__('html').escape(book.title or '')}<br/>{__import__('html').escape(identity_ticket_contributor_line(book))}"
        row.append(Paragraph(ticket_html, ticket_style))
        if len(row) == 3:
            cells.append(row)
            row = []
    if row:
        while len(row) < 3:
            row.append("")
        cells.append(row)

    table = Table(
        cells or [["", "", ""]], colWidths=[64 * mm, 64 * mm, 64 * mm], repeatRows=0
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#9fb8ae")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story = [
        Paragraph(
            "Book Tickets",
            title_style,
        ),
        Spacer(1, 4 * mm),
        table,
    ]
    doc.build(story)
    return buffer.getvalue()


def build_books_pdf_response(books):
    return pdf_response(
        book_export_filename("catalog", "pdf"),
        make_book_list_pdf(books),
    )


def build_book_tickets_pdf_response(books):
    return pdf_response(
        book_export_filename("catalog-tickets", "pdf"),
        make_book_tickets_pdf(books),
    )

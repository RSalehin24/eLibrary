from html import escape

from django.http import HttpResponse

from .grouped_pdf import book_cells
from .tabular import grouped_books


def build_print_response(books, grouping):
    sections = []
    headings = (
        "Book ID / বইয়ের কোড",
        "Title / বই",
        "Contributors / লেখক ও সহযোগী",
        "Categories / বিভাগ",
        "Details / তথ্য",
        "Created (Dhaka) / যোগ হয়েছে (ঢাকা)",
    )
    table_header = "".join(
        f"<th scope='col'>{escape(value)}</th>" for value in headings
    )
    for label, entries in grouped_books(books, grouping):
        rows = "".join(
            "<tr>"
            + "".join(f"<td>{escape(value)}</td>" for value in book_cells(book))
            + "</tr>"
            for book in entries
        )
        sections.append(
            f"<section><h2>{escape(label if grouping else 'Book List / বইয়ের তালিকা')}</h2><table><thead><tr>{table_header}</tr></thead><tbody>{rows}</tbody></table></section>"
        )
    html = (
        """<!doctype html><html lang="bn"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Book List / বইয়ের তালিকা</title><style>
body{font-family:system-ui,'Noto Sans Bengali','Kohinoor Bangla',sans-serif;color:#17251f;margin:20px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #b8c8be;padding:8px;text-align:left;vertical-align:top;white-space:pre-line;overflow-wrap:anywhere}th{background:#e4efe8}h2{font-size:20px}thead{display:table-header-group}tr{break-inside:avoid}.instructions{padding:16px;background:#e4efe8;line-height:1.8}@page{size:A4 landscape;margin:10mm}@media print{body{margin:0}.instructions{display:none}section+section{break-before:page}}
</style></head><body><p class="instructions">প্রিন্ট করুন বা PDF হিসেবে সংরক্ষণ করুন: ব্রাউজারের Print মেনু খুলুন (Ctrl+P / ⌘P), তারপর Save as PDF বেছে নিন।<br>To print or save the complete list as PDF, open the browser’s Print menu (Ctrl+P / ⌘P), then choose Save as PDF.</p>"""
        + "".join(sections)
        + "</body></html>"
    )
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response

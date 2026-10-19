import re
from io import BytesIO
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZIP_DEFLATED, ZipFile

from django.http import HttpResponse

from .tabular import HEADERS, grouped_books, physical_book_row

SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELATIONSHIP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def xml_text(value):
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))


def sheet_names(labels):
    used, names = set(), []
    for label in labels:
        base = re.sub(r"[\\/:*?\[\]]", "_", xml_text(label)).strip(" '") or "Books"
        name, suffix = base[:31], 1
        while name.casefold() in used:
            suffix += 1
            ending = f" ({suffix})"
            name = base[: 31 - len(ending)] + ending
        used.add(name.casefold())
        names.append(name)
    return names


def column_name(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def sheet_xml(books):
    rows = [HEADERS, *(physical_book_row(book) for book in books)]
    output = []
    for number, row in enumerate(rows, 1):
        cells = "".join(
            f'<c r="{column_name(column)}{number}" t="inlineStr"><is>'
            f'<t xml:space="preserve">{escape(xml_text(value))}</t></is></c>'
            for column, value in enumerate(row, 1)
        )
        output.append(f'<row r="{number}">{cells}</row>')
    return (
        XML_HEADER
        + f'<worksheet xmlns="{SPREADSHEET_NS}">'
        + (
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" '
            'topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            "</sheetView></sheetViews><sheetData>"
            + "".join(output)
            + f'</sheetData><autoFilter ref="A1:K{len(rows)}"/></worksheet>'
        )
    )


def workbook_parts(names):
    sheets = "".join(
        f'<sheet name={quoteattr(name)} sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(names, 1)
    )
    relationships = "".join(
        f'<Relationship Id="rId{index}" Type="{RELATIONSHIP_NS}/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(names) + 1)
    )
    return {
        "xl/workbook.xml": XML_HEADER + f'<workbook xmlns="{SPREADSHEET_NS}" '
        f'xmlns:r="{RELATIONSHIP_NS}"><sheets>{sheets}</sheets></workbook>',
        "xl/_rels/workbook.xml.rels": XML_HEADER
        + f'<Relationships xmlns="{PACKAGE_NS}">{relationships}</Relationships>',
        "_rels/.rels": XML_HEADER + f'<Relationships xmlns="{PACKAGE_NS}">'
        f'<Relationship Id="rId1" Type="{RELATIONSHIP_NS}/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>',
    }


def content_types(sheet_count):
    sheets = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return XML_HEADER + (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + sheets
        + "</Types>"
    )


def build_physical_xlsx_response(books, grouping):
    groups = grouped_books(books, grouping)
    names = sheet_names(label for label, _ in groups)
    parts = workbook_parts(names)
    parts["[Content_Types].xml"] = content_types(len(groups))
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for filename, value in parts.items():
            archive.writestr(filename, value)
        for index, (_, entries) in enumerate(groups, 1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml(entries))
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="physical-books.xlsx"'
    return response

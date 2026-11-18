from __future__ import annotations

from html import escape
from io import BytesIO
import re
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


def build_simple_epub(
    title: str,
    sections: list[dict[str, str]] | None = None,
    *,
    language: str = "en",
) -> bytes:
    normalized_sections = sections or [
        {
            "title": "Chapter 1",
            "body": "<p>Seeded EPUB chapter one for reader coverage.</p>",
        },
        {
            "title": "Chapter 2",
            "body": "<p>Seeded EPUB chapter two for reader coverage.</p>",
        },
    ]
    identifier = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "book"
    buffer = BytesIO()

    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=ZIP_STORED,
        )
        archive.writestr(
            "META-INF/container.xml",
            build_container_xml(),
            compress_type=ZIP_DEFLATED,
        )

        manifest_items = [
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        ]
        spine_items = []
        toc_items = []

        for index, section in enumerate(normalized_sections, start=1):
            section_id = f"chapter-{index}"
            href = f"text/{section_id}.xhtml"
            archive.writestr(
                f"OEBPS/{href}",
                build_section_document(
                    title=section.get("title") or f"Chapter {index}",
                    body=section.get("body") or "<p>Seeded EPUB content.</p>",
                    language=language,
                    section_id=section_id,
                ),
                compress_type=ZIP_DEFLATED,
            )
            manifest_items.append(
                f'<item id="{section_id}" href="{href}" media-type="application/xhtml+xml"/>'
            )
            spine_items.append(f'<itemref idref="{section_id}"/>')
            toc_items.append(
                (
                    f'<li><a href="{href}">'
                    f'{escape(section.get("title") or f"Chapter {index}")}'
                    "</a></li>"
                )
            )

        archive.writestr(
            "OEBPS/nav.xhtml",
            build_navigation_document(
                title=title,
                language=language,
                toc_items=toc_items,
            ),
            compress_type=ZIP_DEFLATED,
        )
        archive.writestr(
            "OEBPS/content.opf",
            build_package_document(
                title=title,
                identifier=identifier,
                language=language,
                manifest_items=manifest_items,
                spine_items=spine_items,
            ),
            compress_type=ZIP_DEFLATED,
        )

    return buffer.getvalue()


def build_container_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def build_package_document(
    *,
    title: str,
    identifier: str,
    language: str,
    manifest_items: list[str],
    spine_items: list[str],
) -> str:
    manifest = "\n    ".join(manifest_items)
    spine = "\n    ".join(spine_items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{escape(language)}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:seed:{escape(identifier)}</dc:identifier>
    <dc:title>{escape(title)}</dc:title>
    <dc:language>{escape(language)}</dc:language>
  </metadata>
  <manifest>
    {manifest}
  </manifest>
  <spine>
    {spine}
  </spine>
</package>
"""


def build_navigation_document(
    *,
    title: str,
    language: str,
    toc_items: list[str],
) -> str:
    toc = "\n        ".join(toc_items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{escape(language)}">
  <head>
    <title>{escape(title)}</title>
  </head>
  <body>
    <nav epub:type="toc" id="toc">
      <h1>{escape(title)}</h1>
      <ol>
        {toc}
      </ol>
    </nav>
  </body>
</html>
"""


def build_section_document(
    *,
    title: str,
    body: str,
    language: str,
    section_id: str,
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{escape(language)}">
  <head>
    <title>{escape(title)}</title>
  </head>
  <body>
    <section id="{escape(section_id)}">
      <h1>{escape(title)}</h1>
      {body}
    </section>
  </body>
</html>
"""

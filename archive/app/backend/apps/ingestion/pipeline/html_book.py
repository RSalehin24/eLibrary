import os
from html import escape

from apps.ingestion.pipeline.curated_export import (
    curated_document_to_legacy_payload,
    is_curated_document,
)
from apps.ingestion.services.normalization import (
    dedupe_structured_sections,
    extract_boundary_sections_from_content_items,
    normalize_dedication_heading_and_content,
    split_leading_front_sections,
    split_trailing_front_sections,
)
from .html_book_support.preview import render_preview_single_tab_guard_script
from .html_book_support.styles import generate_css
from .html_book_support.toc import (
    build_hierarchical_toc_html,
    build_toc_id_map,
    display_value,
    generate_content_html,
    html_cover_source,
)
from .epub_properties.labels import detect_book_language, labels_for

def save_html(
    book_title,
    author,
    series,
    book_type,
    cover,
    main_content,
    book_info,
    dedication,
    toc,
    content_items,
    output_folder,
    *,
    front_sections=None,
    back_sections=None,
):
    """Generate and save HTML book with hierarchical TOC, book info and dedication section"""
    existing_ids = set()
    front_sections = list(front_sections or [])
    back_sections = list(back_sections or [])
    compact_main_content = main_content or ""
    labels = labels_for(
        detect_book_language(
            book_title=book_title or "",
            author=author or "",
            book_info_html=book_info or "",
        )
    )

    # Start HTML document
    html = f"""<!DOCTYPE html>
<html lang='{labels["html_lang"]}'>
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(book_title)}</title>
    <style>{generate_css()}</style>{render_preview_single_tab_guard_script()}
  </head>
  <body>
    <div class="container">
      <!-- Book Header -->
      <div class="book-header">
        <h1>{escape(book_title)}</h1>
        <div class="author">{escape(author)}</div>"""

    if series:
        series_label = "Series" if labels["html_lang"] == "en" else "সিরিজ"
        html += f"\n        <div class='series'>{series_label}: {escape(series)}</div>"
    if book_type:
        html += f"\n        <div class='book-type'>{escape(book_type)}</div>"

    html += "\n      </div>"

    # Cover Image
    cover_src = html_cover_source(cover, output_folder)
    if cover_src:
        html += f"\n      <img src='{cover_src}' alt='Book Cover' class='cover-image'>"
    else:
        html += "\n      <div class='cover-placeholder-card'>"
        html += "\n        <span class='cover-placeholder-kicker'>Book</span>"
        html += f"\n        <div><h2 class='cover-placeholder-title'>{escape(book_title)}</h2><p class='cover-placeholder-author'>{escape(author)}</p></div>"
        html += "\n      </div>"

    # Book Info Section (extracted from main content, before dedication)
    if book_info:
        html += "\n      <div class='book-info-section'>"
        html += f"\n        <h2 class='book-info-title'>{escape(labels['info_page'])}</h2>"
        html += "\n        <div class='book-info-content'>"
        indented_info = "\n".join(f"          {line}" for line in book_info.splitlines())
        html += f"\n{indented_info}"
        html += "\n        </div>"
        html += "\n      </div>"

    dedication_title, normalized_dedication_html = normalize_dedication_heading_and_content(dedication or "")

    # Dedication Section (if present)
    if normalized_dedication_html:
        html += "\n      <div class='dedication-section'>"
        html += f"\n        <h2 class='dedication-title'>{escape(dedication_title)}</h2>"
        html += "\n        <div class='dedication-content'>"
        # Insert dedication HTML directly (already contains <p> tags)
        indented_dedication = "\n".join(f"          {line}" for line in normalized_dedication_html.splitlines())
        html += f"\n{indented_dedication}"
        html += "\n        </div>"
        html += "\n      </div>"

    if front_sections:
        for section in front_sections:
            html += "\n      <div class='front-section'>"
            html += f"\n        <h2 class='front-section-title'>{escape(section['title'])}</h2>"
            html += "\n        <div class='front-section-content'>"
            indented_section = "\n".join(f"          {line}" for line in section["html"].splitlines())
            html += f"\n{indented_section}"
            html += "\n        </div>"
            html += "\n      </div>"

    toc_id_map = build_toc_id_map(toc, existing_ids)
    if toc:
        html += "\n      <div class='toc-section'>"
        html += f"\n        <h2 class='toc-title'>{escape(labels['toc'])}</h2>"
        html += "\n        <ul class='toc-list'>"
        toc_html = build_hierarchical_toc_html(toc, toc_id_map)
        html += toc_html
        html += "\n        </ul>"
        html += "\n      </div>"

    # Main Content
    if compact_main_content:
      html += "\n      <div class='main-content'>"
      indented_content = "\n".join(f"        {line}" for line in compact_main_content.splitlines())
      html += f"\n{indented_content}"
      html += "\n      </div>"

    # Content Sections
    html += "\n      <!-- Content Sections -->"
    content_html = generate_content_html(content_items, toc, toc_id_map)
    html += content_html

    for section in back_sections:
        html += "\n      <div class='back-section'>"
        html += f"\n        <h2 class='back-section-title'>{escape(section['title'])}</h2>"
        html += "\n        <div class='back-section-content'>"
        indented_section = "\n".join(f"          {line}" for line in section["html"].splitlines())
        html += f"\n{indented_section}"
        html += "\n        </div>"
        html += "\n      </div>"

    # Close HTML
    html += "\n    </div>"
    html += "\n  </body>"
    html += "\n</html>"

    # Save file
    html_file = os.path.join(output_folder, "book.html")
    if os.path.exists(html_file):
        print(f"Replacing existing HTML file: {html_file}")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML saved at {html_file}")

def create_html_book(book_data):
    """
    Create HTML book from scraped book data.
    
    Expected book_data structure:
    {
        "book_title": str,
        "author": str,
        "series": str,
        "book_type": str,
        "cover": str,
        "main_content": str,
        "book_info": str,           # Book info extracted before dedication
        "dedication": str,          # Dedication text
        "toc": list,              # Hierarchical TOC structure
        "content_items": list,     # List of content dictionaries
        "output_folder": str
    }
    """
    if is_curated_document(book_data):
        book_data = curated_document_to_legacy_payload(book_data)
    canonical_payload = bool(book_data.get("canonical_manifest") or book_data.get("canonical_sections"))

    reference_fragments = [book_data.get("book_info", ""), book_data.get("dedication", "")]
    explicit_front_sections = dedupe_structured_sections(
        book_data.get("front_sections") or [],
        reference_fragments=reference_fragments,
    )
    explicit_back_sections = dedupe_structured_sections(
        book_data.get("back_sections") or [],
        reference_fragments=reference_fragments,
    )
    toc = book_data["toc"]
    content_items = list(book_data["content_items"])
    inferred_front_sections = []
    inferred_back_sections = []
    # Trust source structure when explicit body exists.
    has_explicit_body = bool(toc or content_items)
    if content_items and not canonical_payload:
        (
            inferred_front_sections,
            inferred_back_sections,
            toc,
            content_items,
        ) = extract_boundary_sections_from_content_items(
            content_items,
            toc,
            trust_source_toc=has_explicit_body,
        )
    front_sections = dedupe_structured_sections(
        [*explicit_front_sections, *inferred_front_sections],
        reference_fragments=reference_fragments,
    )
    back_sections = dedupe_structured_sections(
        [*explicit_back_sections, *inferred_back_sections],
        reference_fragments=reference_fragments,
    )
    main_content = book_data["main_content"]
    compact_main_content = main_content
    if not front_sections and not canonical_payload:
        front_sections, compact_main_content = split_leading_front_sections(
            main_content or "",
            has_explicit_body=has_explicit_body,
        )
    if not back_sections and not canonical_payload and not has_explicit_body:
        back_sections, compact_main_content = split_trailing_front_sections(compact_main_content or "")

    save_html(
        book_title=book_data["book_title"],
        author=display_value(book_data["author"]),
        series=display_value(book_data["series"]),
        book_type=display_value(book_data["book_type"]),
        cover=book_data["cover"],
        main_content=compact_main_content,
        book_info=book_data.get("book_info", ""),
        dedication=book_data.get("dedication", ""),
        toc=toc,
        content_items=content_items,
        output_folder=book_data["output_folder"],
        front_sections=front_sections,
        back_sections=back_sections,
    )

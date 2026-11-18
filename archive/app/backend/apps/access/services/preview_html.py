import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from apps.catalog.models import GeneratedAssetType
from apps.ingestion.services.normalization import (
    normalize_dedication_heading_and_content,
    promote_leading_front_matter,
    split_leading_front_sections,
)
from apps.access.views.shared import local_asset_path, read_asset_bytes


def build_data_uri(path):
    mime_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    encoded_image = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded_image}"


def is_local_preview_src(src):
    if not src:
        return False
    parsed = urlsplit(src)
    if parsed.scheme or parsed.netloc:
        return False
    if src.startswith(("/", "#")):
        return False
    return parsed.path != ""


def is_cover_reference(image_tag, requested_name):
    classes = set(image_tag.get("class", []))
    alt_text = (image_tag.get("alt") or "").lower()
    stem = Path(requested_name).stem.lower()
    return "cover-image" in classes or "cover" in alt_text or stem in {"book_cover", "book_image"}


def resolve_preview_image_path(source_dir, requested_src, image_tag, cover_path=None):
    if source_dir is None or not source_dir.exists():
        source_dir = None

    requested_name = Path(unquote(urlsplit(requested_src).path)).name
    requested_stem = Path(requested_name).stem

    if source_dir and requested_name:
        direct_path = source_dir / requested_name
        if direct_path.is_file():
            return direct_path
        if requested_stem:
            for candidate in sorted(source_dir.iterdir()):
                if candidate.is_file() and candidate.stem == requested_stem:
                    return candidate

    if is_cover_reference(image_tag, requested_name):
        if cover_path and cover_path.exists():
            return cover_path
        if source_dir:
            for fallback_stem in ("book_cover", "book_image"):
                for candidate in sorted(source_dir.glob(f"{fallback_stem}.*")):
                    if candidate.is_file():
                        return candidate
    return None


def replace_tag_contents(tag, html_fragment):
    tag.clear()
    fragment = BeautifulSoup(html_fragment, "html.parser")
    container = fragment.body if fragment.body else fragment
    for child in list(container.contents):
        tag.append(child)


def build_book_info_section(html_fragment):
    fragment = BeautifulSoup(
        """
        <div class="book-info-section">
          <h2 class="book-info-title">বই তথ্য</h2>
          <div class="book-info-content"></div>
        </div>
        """,
        "html.parser",
    )
    section = fragment.find("div", class_="book-info-section")
    replace_tag_contents(section.find("div", class_="book-info-content"), html_fragment)
    return section


def build_dedication_section(html_fragment, title):
    fragment = BeautifulSoup(
        f"""
        <div class="dedication-section">
          <h2 class="dedication-title">{title}</h2>
          <div class="dedication-content"></div>
        </div>
        """,
        "html.parser",
    )
    section = fragment.find("div", class_="dedication-section")
    replace_tag_contents(section.find("div", class_="dedication-content"), html_fragment)
    return section


def build_front_section(title, html_fragment):
    fragment = BeautifulSoup(
        f"""
        <div class="front-section">
          <h2 class="front-section-title">{title}</h2>
          <div class="front-section-content"></div>
        </div>
        """,
        "html.parser",
    )
    section = fragment.find("div", class_="front-section")
    replace_tag_contents(section.find("div", class_="front-section-content"), html_fragment)
    return section


def normalize_preview_book_sections(soup, dedication_html=""):
    main_content = soup.find("div", class_="main-content")
    container = soup.find("div", class_="container")
    insertion_anchor = main_content or soup.find("div", class_="toc-section")
    front_section_anchor = main_content or insertion_anchor
    updated = False

    if main_content is not None:
        book_info_content = soup.find("div", class_="book-info-content")
        current_book_info_html = book_info_content.decode_contents() if book_info_content else ""
        current_main_content_html = main_content.decode_contents()
        promoted_book_info_html, cleaned_main_content_html = promote_leading_front_matter(
            current_book_info_html,
            current_main_content_html,
        )
        if cleaned_main_content_html != current_main_content_html:
            replace_tag_contents(main_content, cleaned_main_content_html)
            updated = True

        front_sections, compact_main_content_html = split_leading_front_sections(main_content.decode_contents())
        if compact_main_content_html != main_content.decode_contents():
            replace_tag_contents(main_content, compact_main_content_html)
            updated = True

        if front_sections and front_section_anchor is not None:
            for section in front_sections:
                front_section_anchor.insert_before(build_front_section(section["title"], section["html"]))
            updated = True

        if promoted_book_info_html and promoted_book_info_html != current_book_info_html:
            if book_info_content is None:
                main_content.insert_before(build_book_info_section(promoted_book_info_html))
            else:
                replace_tag_contents(book_info_content, promoted_book_info_html)
            updated = True

    raw_book_dedication_html = (dedication_html or "").strip()
    dedication_content = soup.find("div", class_="dedication-content")
    if dedication_content is not None:
        current_dedication_html = dedication_content.decode_contents()
        dedication_title_tag = soup.find("h2", class_="dedication-title")
        dedication_title, normalized_dedication_html = normalize_dedication_heading_and_content(
            current_dedication_html or raw_book_dedication_html
        )
        if dedication_title_tag is not None and dedication_title_tag.get_text(strip=True) != dedication_title:
            dedication_title_tag.string = dedication_title
            updated = True
        if normalized_dedication_html != current_dedication_html:
            replace_tag_contents(dedication_content, normalized_dedication_html)
            updated = True
    elif raw_book_dedication_html:
        dedication_title, normalized_dedication_html = normalize_dedication_heading_and_content(raw_book_dedication_html)
        if normalized_dedication_html:
            dedication_section = build_dedication_section(normalized_dedication_html, dedication_title)
            if insertion_anchor is not None:
                insertion_anchor.insert_before(dedication_section)
                updated = True
            elif container is not None:
                container.append(dedication_section)
                updated = True
            elif soup.body is not None:
                soup.body.append(dedication_section)
                updated = True
    return updated


def normalize_preview_html(book, asset):
    html_bytes, _, source_path = read_asset_bytes(asset)
    html_text = html_bytes.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html_text, "html.parser")
    source_dir = source_path.parent if source_path else None
    cover_asset = book.generated_assets.filter(asset_type=GeneratedAssetType.COVER).first()
    cover_path = local_asset_path(cover_asset)
    updated = normalize_preview_book_sections(soup, dedication_html=book.dedication_html)

    for image_tag in soup.find_all("img"):
        src = (image_tag.get("src") or "").strip()
        if not is_local_preview_src(src):
            continue
        resolved_path = resolve_preview_image_path(source_dir, src, image_tag, cover_path=cover_path)
        if resolved_path is None:
            continue
        image_tag["src"] = build_data_uri(resolved_path)
        updated = True

    return soup.decode() if updated else html_text


__all__ = ["normalize_preview_book_sections", "normalize_preview_html"]

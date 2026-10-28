import hashlib
import re
from html import escape
from urllib.parse import urlsplit
from uuid import uuid4

from apps.access.reading.epub_paths import InvalidEpub, referenced_path
from apps.access.reading.preparation import (
    publication_directory,
    publication_files_available,
)
from apps.catalog.models import GeneratedAsset
from bs4 import BeautifulSoup
from bs4.element import Tag
from django.core.files.base import ContentFile

from .epub_html_resources import MAX_HTML_BYTES, HtmlResources


def scope_stylesheet(stylesheet, section):
    # Complex CSS must fail conversion instead of silently changing the book.
    stylesheet = re.sub(r"/\*.*?\*/", "", stylesheet, flags=re.DOTALL)
    pattern = r"([^{}]+)\{([^{}]*)\}"
    if re.sub(pattern, "", stylesheet).strip():
        raise InvalidEpub("The EPUB stylesheet needs unsupported conversion.")
    rules = []
    for selectors, declarations in re.findall(pattern, stylesheet):
        if selectors.strip() == "@font-face":
            rules.append(f"@font-face {{{declarations}}}")
            continue
        if "@" in selectors:
            raise InvalidEpub("The EPUB stylesheet needs unsupported conversion.")
        declarations = scoped_fragment_urls(declarations, section)
        selectors = re.sub(r"#([\w-]+)", rf"#{section}--\1", selectors)
        selectors = re.sub(r"\b(?:html|body)\b|:root", ".epub-body", selectors)
        scoped = [f"#{section} {selector.strip()}" for selector in selectors.split(",")]
        rules.append(f"{','.join(scoped)} {{{declarations}}}")
    return "\n".join(rules)


def scoped_fragment_urls(value, section):
    return re.sub(r"(url\(\s*['\"]?)#([\w-]+)", rf"\1#{section}--\2", value)


def rewrite_element(element, chapter, resources):
    path, section = chapter
    if element.get("id"):
        element["id"] = f"{section}--{element['id']}"
    for attribute in ("src", "poster", "xlink:href"):
        if element.get(attribute):
            element[attribute] = resources.data_uri(path, str(element[attribute]))
    if element.get("href"):
        reference = str(element["href"])
        if element.name == "a" and urlsplit(reference).scheme.lower() in {
            "http",
            "https",
        }:
            element["rel"] = "noopener noreferrer"
        else:
            element["href"] = resources.anchor(path, reference)
    if element.get("srcset") or element.name in {
        "form",
        "input",
        "button",
        "iframe",
        "object",
        "embed",
        "script",
    }:
        raise InvalidEpub("The EPUB contains unsupported interactive content.")
    if element.get("style"):
        element["style"] = scoped_fragment_urls(
            resources.style(path, str(element["style"])), section
        )


def chapter_html(path, resources):
    document = BeautifulSoup(resources.text(path), "html.parser")
    body = document.body
    if body is None:
        raise InvalidEpub("An EPUB chapter has no body.")
    section = resources.sections[path]
    body.name = "div"
    body["class"] = " ".join([*map(str, body.get_attribute_list("class")), "epub-body"])
    rewrite_element(body, (path, section), resources)
    styles = []
    for node in document.select("style, link[rel~=stylesheet]"):
        base = referenced_path(path, str(node["href"])) if node.name == "link" else path
        value = resources.text(base) if node.name == "link" else node.get_text()
        styles.append(scope_stylesheet(resources.style(base, value), section))
        node.extract()
    for element in body.find_all(True):
        if isinstance(element, Tag):
            rewrite_element(element, (path, section), resources)
    return f'<style>{"".join(styles)}</style><section id="{section}">{body}</section>'


def stage_epub_html(book, publication):
    if not publication_files_available(publication):
        raise InvalidEpub("The EPUB reader resources are incomplete.")
    resources = HtmlResources(publication, publication_directory(publication))
    chapters = converted_chapters(publication, resources)
    content = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{escape(book.title)}</title></head><body>{''.join(chapters)}</body></html>"
    ).encode()
    if len(content) > MAX_HTML_BYTES:
        raise InvalidEpub("The converted EPUB exceeds the HTML size limit.")
    asset = GeneratedAsset(
        book=book,
        asset_type="html",
        status="ready",
        content_type="text/html; charset=utf-8",
    )
    asset.file.save(f"{uuid4().hex}.html", ContentFile(content), save=False)
    asset.storage_path, asset.file_size = asset.file.name or "", len(content)
    asset.checksum = hashlib.sha256(content).hexdigest()
    return asset


def converted_chapters(publication, resources):
    chapters, size, readable = [], 0, False
    for chapter in publication.manifest["chapters"]:
        content = chapter_html(chapter["path"], resources)
        size += len(content.encode())
        if size > MAX_HTML_BYTES:
            raise InvalidEpub("The converted EPUB exceeds the HTML size limit.")
        body = BeautifulSoup(content, "html.parser")
        readable = readable or bool(
            body.get_text(strip=True) or body.find(["img", "svg", "audio", "video"])
        )
        chapters.append(content)
    if not readable:
        raise InvalidEpub("The EPUB contains no reading content.")
    return chapters

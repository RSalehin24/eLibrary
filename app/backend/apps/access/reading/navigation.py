import logging
import re
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from .epub_archive import MAX_XML_BYTES, read_entry
from .epub_paths import InvalidEpub, referenced_path

MAX_NAVIGATION_DEPTH = 8
MAX_NAVIGATION_ENTRIES = 2000
logger = logging.getLogger(__name__)


def publication_navigation(archive, resources, chapters):
    candidates = sorted(
        (item for item in resources.values() if item.get("navigation_type")),
        key=lambda item: item["navigation_type"] != "nav",
    )
    for resource in candidates:
        try:
            entries = navigation_entries(archive, resource, chapters)
        except (InvalidEpub, UnicodeError, ValueError, ElementTree.ParseError):
            logger.warning("An EPUB contents document could not be used.")
            continue
        if entries:
            return entries
    return []


def navigation_entries(archive, resource, chapters):
    entry = archive.getinfo(resource["path"])
    if entry.file_size > MAX_XML_BYTES:
        raise InvalidEpub("EPUB contents exceed the metadata limit.")
    document = navigation_document(read_entry(archive, entry))
    root = navigation_root(document, resource["navigation_type"])
    return flatten_navigation(root, (resource, chapters)) if root is not None else []


def navigation_root(document, kind):
    if kind == "ncx":
        return next(
            (node for node in document.iter() if local_name(node) == "navmap"), None
        )
    root = next((node for node in document.iter() if is_contents_nav(node)), None)
    return child_named(root, {"ol"}) if root is not None else None


def is_contents_nav(node):
    return local_name(node) == "nav" and (
        "toc" in node.get("{http://www.idpf.org/2007/ops}type", "").split()
        or node.get("role") == "doc-toc"
    )


def navigation_document(data):
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    # Navigation does not need a DTD; discard external declarations without fetching it.
    text = re.sub(
        r"<!DOCTYPE\s+(?:html|ncx)\b[^<>\[\]]*>",
        "",
        data.decode(encoding),
        flags=re.IGNORECASE,
    )
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
        raise InvalidEpub("EPUB contents declarations are unsupported.")
    return ElementTree.fromstring(text)


def local_name(node):
    return node.tag.rsplit("}", 1)[-1].lower()


def child_named(node, names):
    return next((child for child in node if local_name(child) in names), None)


def navigation_target(href, context):
    resource, chapters = context
    try:
        path = referenced_path(resource["path"], href)
        fragment = unquote(urlsplit(href).fragment, errors="strict")
    except (InvalidEpub, ValueError, UnicodeError):
        return None
    if len(fragment) > 512:
        return None
    index = next(
        (index for index, chapter in enumerate(chapters) if chapter["path"] == path),
        None,
    )
    return (index, fragment) if index is not None else None


def navigation_item(item, context):
    ncx = context[0]["navigation_type"] == "ncx"
    label = child_named(item, {"navlabel"} if ncx else {"a", "span"})
    link = child_named(item, {"content"}) if ncx else label
    target = (
        navigation_target(str(link.get("src" if ncx else "href", "")), context)
        if link is not None
        else None
    )
    return (
        " ".join(" ".join(label.itertext()).split())[:255] if label is not None else "",
        target,
    )


def navigation_children(element, kind):
    return (
        [
            child
            for child in element
            if local_name(child) == ("navpoint" if kind == "ncx" else "li")
        ]
        if element is not None
        else []
    )


def navigation_record(item, context, depth):
    kind = context[0]["navigation_type"]
    label, target = navigation_item(item, context)
    children = navigation_children(
        item if kind == "ncx" else child_named(item, {"ol"}), kind
    )
    record = {
        "label": label,
        "chapter_index": target[0] if target else None,
        "fragment": target[1] if target else "",
        "depth": depth,
    }
    return (record if label and (target or children) else None), children


def flatten_navigation(root, context):
    result: list[dict[str, str | int | None]] = []
    pending = [
        (item, 0)
        for item in reversed(navigation_children(root, context[0]["navigation_type"]))
    ]
    while pending:
        item, depth = pending.pop()
        if depth > MAX_NAVIGATION_DEPTH or len(result) >= MAX_NAVIGATION_ENTRIES:
            raise InvalidEpub("EPUB contents exceed the navigation limit.")
        record, children = navigation_record(item, context, depth)
        if record:
            result.append(record)
        pending.extend((child, depth + 1) for child in reversed(children))
    return result

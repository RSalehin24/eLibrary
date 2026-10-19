from bs4 import BeautifulSoup

from apps.ingestion.services.normalization import (
    BOOK_INFO_KEY_LABELS_BN,
    combined_front_matter_html,
    extract_front_matter_entries,
)

MAX_HTML_CHARACTERS = 65536
MAX_TEXT_CHARACTERS = 8000
MAX_FRONT_MATTER_ENTRIES = 50
MAX_METADATA_LABEL_CHARACTERS = 100
MAX_METADATA_VALUE_CHARACTERS = 2000
MAX_CONTENTS_ENTRIES = 200
MAX_CONTENTS_DEPTH = 8
MAX_CONTENTS_VISITS = 1000
MAX_CONTENTS_LABEL_CHARACTERS = 500
END_CONTENTS = object()


def plain_preview(value):
    soup = BeautifulSoup(value[:MAX_HTML_CHARACTERS], "html.parser")
    for element in soup(["script", "style", "template", "noscript"]):
        element.decompose()
    text = soup.get_text("\n", strip=True)
    return text[:MAX_TEXT_CHARACTERS], (
        len(value) > MAX_HTML_CHARACTERS or len(text) > MAX_TEXT_CHARACTERS
    )


def child_contents(node, depth):
    children = node.get("children")
    if not isinstance(children, list) or not children:
        return None, False
    if depth > MAX_CONTENTS_DEPTH:
        return None, True
    return iter(children), False


def contents_preview(nodes):
    entries: list[dict[str, str | int]] = []
    truncated = False
    pending = [iter(nodes if isinstance(nodes, list) else [])]
    visits = 0
    while pending and len(entries) < MAX_CONTENTS_ENTRIES and visits < MAX_CONTENTS_VISITS:
        visits += 1
        node = next(pending[-1], END_CONTENTS)
        if node is END_CONTENTS:
            pending.pop()
            continue
        if not isinstance(node, dict):
            continue
        label, shortened = plain_preview(str(node.get("title") or node.get("label") or ""))
        truncated = truncated or shortened or len(label) > MAX_CONTENTS_LABEL_CHARACTERS
        if label:
            entries.append({"label": label[:MAX_CONTENTS_LABEL_CHARACTERS], "depth": len(pending) - 1})
        children, shortened = child_contents(node, len(pending))
        truncated = truncated or shortened
        if children is not None:
            pending.append(children)
    return entries, truncated or any(next(level, END_CONTENTS) is not END_CONTENTS for level in pending)


def front_matter_preview(book):
    front_html = combined_front_matter_html(
        book.book_info_html[:MAX_HTML_CHARACTERS],
        book.main_content_html[:MAX_HTML_CHARACTERS],
    )
    front_text, front_truncated = plain_preview(front_html)
    entries = extract_front_matter_entries(front_html[:MAX_HTML_CHARACTERS])
    metadata = [
        {"label": BOOK_INFO_KEY_LABELS_BN.get(entry["key"], entry["label"])[:MAX_METADATA_LABEL_CHARACTERS], "value": entry["value"][:MAX_METADATA_VALUE_CHARACTERS]}
        for entry in entries if not entry["role"]
    ]
    truncated = (
        front_truncated or len(book.book_info_html) > MAX_HTML_CHARACTERS
        or len(metadata) > MAX_FRONT_MATTER_ENTRIES
        or any(len(entry["value"]) > MAX_METADATA_VALUE_CHARACTERS or len(entry["label"]) > MAX_METADATA_LABEL_CHARACTERS for entry in entries)
    )
    return metadata[:MAX_FRONT_MATTER_ENTRIES], "" if metadata else front_text, truncated


def book_detail_preview(book):
    front_matter, front_text, front_truncated = front_matter_preview(book)
    dedication, dedication_truncated = plain_preview(book.dedication_html)
    contents, contents_truncated = contents_preview(book.toc)
    return {
        "front_matter": front_matter,
        "front_matter_text": front_text,
        "dedication": dedication,
        "contents": contents,
        "truncated": front_truncated or dedication_truncated or contents_truncated,
    }

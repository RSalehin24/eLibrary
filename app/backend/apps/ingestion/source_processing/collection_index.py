from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .classification import inline_classification

CONTENTS_LABELS = {"সূচি", "সূচিপত্র", "contents", "table of contents"}
MAX_COLLECTION_DEPTH = 8


@dataclass(frozen=True)
class LinkedBook:
    title: str
    url: str


def linked_list_entries(block, source_url):
    entries = []
    for item in block.find_all("li", recursive=False):
        anchors = item.select("a[href]")
        if len(anchors) != 1:
            return []
        anchor = anchors[0]
        url = urlsplit(urljoin(source_url, anchor["href"]))
        if (
            not url.path.startswith("/books/")
            or len(url.path.strip("/").split("/")) != 2
        ):
            return []
        if url.fragment and url.path.rstrip("/") == urlsplit(source_url).path.rstrip(
            "/"
        ):
            return []
        title = anchor.get_text(" ", strip=True)
        if not title or item.get_text(" ", strip=True) != title:
            return []
        entries.append(LinkedBook(title, urlunsplit(url._replace(fragment=""))))
    return (
        entries
        if len(entries) >= 2 and len({entry.url for entry in entries}) == len(entries)
        else []
    )


def linked_book_entries(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    reading = inline_classification(html) == "inline_reading"
    for block in soup.select("ul,ol"):
        previous = block.find_previous_sibling()
        label = (
            previous.get_text(" ", strip=True).lower().rstrip(" :：।")
            if previous
            else ""
        )
        # Ordinary references inside a readable work must not become component books.
        if reading and label not in CONTENTS_LABELS:
            continue
        entries = linked_list_entries(block, source_url)
        if entries:
            return entries
    return []

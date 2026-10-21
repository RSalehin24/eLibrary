import re

from bs4 import BeautifulSoup

from .content_text import canonical_text

VALIDATOR_VERSION = 3
DESCRIPTION_PATTERN = re.compile(
    r"(?:\bis\s+(?:a|an|the)\b.{0,100}\b(?:novel|comedy|play|collection|book)\b"
    r"|\b(?:portrays|published in|written (?:in|around)|the story (?:follows|revolves))\b"
    r"|(?:উপন্যাসটি|বইটি|গ্রন্থটি|নাটকটি).{0,100}(?:রচিত|প্রকাশিত|রচনা|সম্পর্কে))",
    re.IGNORECASE,
)
READING_HEADING = re.compile(
    r"(?:অধ্যা[য়য]|পরিচ্ছেদ|পর্ব|খণ্ড|কাণ্ড|সর্গ|মূল লেখা|মূল পাঠ|\bchapter\b|\bact\b|\bscene\b|\bpart\b)",
    re.IGNORECASE,
)


def inline_classification(html):
    soup = BeautifulSoup(html, "html.parser")
    text = canonical_text(html)
    if not text:
        return "unavailable_content"
    paragraphs = [canonical_text(str(tag)) for tag in soup.select("p")]
    if DESCRIPTION_PATTERN.search(" ".join(paragraphs[:2])):
        return "description_only"
    headings = " ".join(
        tag.get_text(" ", strip=True) for tag in soup.select("h1,h2,h3,h4")
    )
    if READING_HEADING.search(headings) or soup.select(".poem,.poetry,pre,blockquote"):
        return "inline_reading"
    # Later references to publications are ordinary prose, not landing-page synopses.
    if len(paragraphs) >= 3 or len(soup.select("br")) >= 3:
        return "inline_reading"
    return "unknown_layout"


def classify_source(snapshot):
    from .collection_index import linked_book_entries

    payload = snapshot.get("raw_scrape_payload", {})
    items = payload.get("content_items", [])
    if items:
        return "chaptered_book"
    html = payload.get("main_content", "")
    if linked_book_entries(html, snapshot.get("canonical_url", "")):
        return "linked_collection"
    return inline_classification(html)


def classification_evidence(snapshot):
    classification = classify_source(snapshot)
    return {
        "validator_version": VALIDATOR_VERSION,
        "classification": classification,
        "reading_content": classification in {"chaptered_book", "inline_reading"},
    }

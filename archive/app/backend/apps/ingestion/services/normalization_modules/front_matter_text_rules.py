import re
from html import escape

from bs4 import BeautifulSoup, Tag

from apps.catalog.models import ContributorRole
from apps.catalog.services import normalize_book_contributors
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.services.normalization_support.metadata import (
    ALL_METADATA_LABELS,
    EXPLICIT_SEPARATOR_ONLY_LABELS,
    FRONT_MATTER_PATTERNS,
    METADATA_LABEL_ALIASES,
    ROLE_PATTERNS,
    canonical_role,
    clean_contributor_value,
    extract_contributor_evidence,
    has_non_name_phrase_marker,
    is_role_label_text,
    looks_like_contributor_name,
    match_pattern_key,
    parse_role_labeled_segment,
    roles_in_text,
    split_contributor_value,
    split_metadata_fragments,
    split_multi_value,
)

DEDICATION_PATTERNS = [
    "উৎসর্গ",
    "অনুবাদকের উৎসর্গ",
    "লেখকের উৎসর্গ",
    "dedication",
]
INLINE_TOC_HEADING_PATTERNS = [
    "সূচীপত্র",
    "সুচিপত্র",
    "সূচী",
    "table of contents",
    "contents",
]
SOURCE_GENERATED_TOC_SELECTORS = (
    ".ftwp-in-post",
    ".ftwp-wrap",
    "#ftwp-container-outer",
    "#ftwp-container",
    "#ftwp-contents",
)

DEDICATION_INLINE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:অনুবাদকের\s+উৎসর্গ|লেখকের\s+উৎসর্গ|উৎসর্গ|dedication)\s*[:ঃ\-–—]?\s*",
    re.IGNORECASE,
)

BODY_SECTION_PATTERNS = [
    "ভূমিকা",
    "প্রস্তাবনা",
    "লেখকের কথা",
    "অনুবাদকের কথা",
    "সম্পাদকের কথা",
    "সংকলকের কথা",
    "প্রকাশকের কথা",
    "সূচিপত্র",
    "সূচীপত্র",
    "সূচী",
    "অধ্যায়",
    "অধ্যায়",
    "পর্ব",
    "খণ্ড",
    "পরিচ্ছেদ",
    "chapter",
    "section",
    "part",
    "preface",
    "introduction",
]

SUPPLEMENTARY_CHAPTER_HEADING_PATTERNS = [
    "নমুনা অধ্যায়",
    "নমুনা অধ্যায়",
    "প্রিভিউ অধ্যায়",
    "প্রিভিউ অধ্যায়",
    "sample chapter",
    "preview chapter",
    "excerpt",
]

FRONT_SECTION_HEADING_PATTERNS = [
    "ভূমিকা",
    "প্রস্তাবনা",
    "লেখকের কথা",
    "অনুবাদকের কথা",
    "অনুবাদকের নিবেদন",
    "অনুবাদকের ভূমিকা",
    "সম্পাদকের কথা",
    "সম্পাদকের নিবেদন",
    "সম্পাদকের ভূমিকা",
    "সম্পাদকীয়",
    "সংকলকের কথা",
    "সংকলকের নিবেদন",
    "প্রকাশকের কথা",
    "প্রকাশকের নিবেদন",
    "দ্বিতীয় সংস্করণের কথা",
    "দ্বিতীয় সংস্করণের কথা",
    "তৃতীয় সংস্করণের কথা",
    "তৃতীয় সংস্করণের কথা",
    "পরিবর্ধিত সংস্করণের কথা",
    "সংস্করণ প্রসঙ্গে",
    "সহস্রাব্দ সংস্করণের কথা",
    "প্রারম্ভ কথন",
    "প্রারম্ভকথন",
    "কথন",
    "foreword",
    "introduction",
    "preface",
    "translator's note",
    "editor's note",
    "publisher's note",
    "edition note",
    "second edition note",
    "afterword",
    *SUPPLEMENTARY_CHAPTER_HEADING_PATTERNS,
]

SEPARATOR_PARAGRAPH_VALUES = {".", "।", "..", "..."}
BLOCK_TAG_NAMES = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote")
HEADING_TAG_NAMES = {"h1", "h2", "h3", "h4", "h5", "h6"}
MAX_METADATA_TEXT_LENGTH = 320
MAX_METADATA_VALUE_LENGTH = 180
MAX_TITLE_PREFIX_LENGTH = 140
MAX_DEDICATION_BLOCK_LENGTH = 600
DATE_LINE_PATTERN = re.compile(
    r"^(?:[০-৯]{1,2}|[0-9]{1,2})\s+(?:জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর|january|february|march|april|may|june|july|august|september|october|november|december)\s*,?\s*(?:[০-৯]{4}|[0-9]{4})$",
    re.IGNORECASE,
)
LETTER_SALUTATION_PATTERN = re.compile(r"^(?:প্রিয়|শ্রদ্ধেয়|dear)\b", re.IGNORECASE)
LETTER_EXCERPT_PATTERNS = [
    "চিঠি",
    "চিঠির",
    "চিঠিতে",
    "পাঠানো চিঠি",
    "letter",
]
def plain_text_from_html(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


def count_sentence_markers(text):
    return len(re.findall(r"[।.!?]", text))


def text_matches_patterns(text, patterns):
    lowered = clean_display_text(text).lower()
    normalized = normalize_catalog_text(text)
    for pattern in patterns:
        cleaned_pattern = clean_display_text(pattern)
        if not cleaned_pattern:
            continue
        if cleaned_pattern.lower() in lowered:
            return True
        if normalize_catalog_text(cleaned_pattern) in normalized:
            return True
    return False


def heading_matches_patterns(text, patterns):
    normalized = normalize_catalog_text(text)
    if not normalized:
        return False
    for pattern in patterns:
        normalized_pattern = normalize_catalog_text(pattern)
        if not normalized_pattern:
            continue
        if normalized == normalized_pattern or normalized.startswith(
            f"{normalized_pattern} ",
        ):
            return True
    return False


def remove_inline_toc_heading_and_lists(block):
    current_block = block
    while current_block is not None:
        next_block = current_block.find_next_sibling()
        if current_block.parent is not None:
            current_block.decompose()
        if next_block is None or next_block.name not in {"ul", "ol"}:
            break
        current_block = next_block


def remove_source_generated_toc_containers(soup):
    for selector in SOURCE_GENERATED_TOC_SELECTORS:
        for block in list(soup.select(selector)):
            if block.parent is not None:
                block.decompose()


def is_probable_inline_toc_list(block):
    if block.name not in {"ul", "ol"}:
        return False
    items = [
        clean_display_text(item.get_text(" ", strip=True))
        for item in block.find_all("li", recursive=False)
    ]
    return bool(items) and all(item and len(item) <= 140 for item in items)


def strip_leading_probable_toc_lists(soup):
    root = soup.find()
    if root is None:
        return

    while True:
        first_child = next(
            (child for child in root.children if isinstance(child, Tag)),
            None,
        )
        if first_child is None or not is_probable_inline_toc_list(first_child):
            break
        first_child.decompose()


def is_separator_paragraph(text):
    return clean_display_text(text).strip(" :ঃ-–—") in SEPARATOR_PARAGRAPH_VALUES


_DOT_TEXT_DOT_RE = re.compile(r"^\.\s+\S.*\s+\.$")


def is_dot_bracketed_section_boundary(text):
    """Detect a Bengali decorative section separator of the form '. text .' (dot–space–text–space–dot).

    In Bengali typography this pattern (e.g. '. তিন .' or '. ০ .') acts as a
    visual divider between two front-matter sections and should be treated as a
    section boundary rather than ordinary body text.
    """
    cleaned = clean_display_text(text).strip(" :ঃ-–—")
    return bool(_DOT_TEXT_DOT_RE.match(cleaned))


def block_text(block):
    return clean_display_text(block.get_text(" ", strip=True))


def block_strong_text(block):
    return clean_display_text(" ".join(strong.get_text(" ", strip=True) for strong in block.find_all("strong")))


def block_has_break(block):
    return block.find("br") is not None


def block_text_lines(block):
    return [
        clean_display_text(line)
        for line in block.get_text("\n", strip=True).splitlines()
        if clean_display_text(line)
    ]


def block_strong_text_lines(block):
    lines = []
    for strong in block.find_all("strong"):
        lines.extend(
            clean_display_text(line)
            for line in strong.get_text("\n", strip=True).splitlines()
            if clean_display_text(line)
        )
    return lines


def join_heading_lines(lines):
    cleaned_lines = [clean_display_text(line) for line in lines if clean_display_text(line)]
    if not cleaned_lines:
        return ""
    if len(cleaned_lines) == 1:
        return cleaned_lines[0]
    return "\n".join(cleaned_lines)


def heading_plain_text(text):
    if not text:
        return ""
    return clean_display_text(str(text).replace("\n", " "))


def block_strong_heading_text(block):
    strong_lines = block_strong_text_lines(block)
    if not strong_lines:
        return ""

    text_lines = block_text_lines(block)
    if not text_lines:
        return ""

    if normalize_catalog_text(" ".join(strong_lines)) != normalize_catalog_text(" ".join(text_lines)):
        return ""

    return join_heading_lines(strong_lines)


_NUMERIC_SECTION_MARKER_RE = re.compile(r"^[০-৯0-9]{1,4}(?:\s*[.)।])?$")


def is_likely_section_title_text(text):
    plain_text = heading_plain_text(text)
    if not plain_text or len(plain_text) > 180:
        return False
    if _NUMERIC_SECTION_MARKER_RE.match(plain_text) and len(plain_text) <= 8:
        # Bare numeric markers like "০১.", "১২." are in-body scene enumerators
        # in novels, not chapter / front-matter titles. Refusing to treat them
        # as section titles prevents `split_leading_front_sections` and
        # `split_trailing_front_sections` from shredding a real lesson body.
        return False
    if text_matches_patterns(plain_text, DEDICATION_PATTERNS + BODY_SECTION_PATTERNS):
        return False
    has_line_break = "\n" in str(text)
    metadata_candidate = search_front_matter_label_value(
        plain_text,
        strong_text=plain_text,
        has_break=has_line_break,
    )
    if metadata_candidate and not has_line_break:
        return False
    if looks_like_letter_excerpt_marker(plain_text):
        return False
    if len(plain_text.split()) > 18:
        return False
    return count_sentence_markers(plain_text) <= 1


def is_non_dedication_strong_heading(text, strong_text="", tag_name=""):
    if tag_name in HEADING_TAG_NAMES:
        return False

    cleaned_text = clean_display_text(text)
    cleaned_strong = clean_display_text(strong_text)
    if not cleaned_text or not cleaned_strong or cleaned_text != cleaned_strong:
        return False
    if is_dedication_heading(cleaned_text, strong_text=strong_text, tag_name=tag_name):
        return False
    return is_likely_section_title_text(cleaned_strong)

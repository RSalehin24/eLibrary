"""Localized labels for EPUB static pages and book-info field names.

Used by :class:`EpubBuilder` and :func:`format_book_info_html_ordered` so that
English-language books render their structural page titles and metadata labels
in English instead of Bengali.
"""

import re

# Bengali Unicode block: U+0980–U+09FF.
_BENGALI_CHAR_RE = re.compile(r"[\u0980-\u09FF]")
_LATIN_CHAR_RE = re.compile(r"[A-Za-z]")


def detect_book_language(book_title="", author="", book_info_html=""):
    """Return ``"en"`` for English-language books, otherwise ``"bn"``.

    Heuristic (in priority order):
    1. If the book title contains Latin letters and no Bengali characters,
       treat the book as English. Author is intentionally ignored because
       on the source site author names are routinely transliterated into
       Bengali even for English-language works (e.g. Hamlet's creator
       reads "উইলিয়াম শেক্সপিয়ার").
    2. If the title is empty or ambiguous, fall back to scanning the
       combined title/author/book_info sample.
    3. Default to Bengali (the site's primary language).
    """
    title = str(book_title or "")
    if title:
        if _BENGALI_CHAR_RE.search(title):
            return "bn"
        if _LATIN_CHAR_RE.search(title):
            return "en"

    sample = " ".join(str(s or "") for s in (author, book_info_html))
    if _BENGALI_CHAR_RE.search(sample):
        return "bn"
    if _LATIN_CHAR_RE.search(sample):
        return "en"
    return "bn"


# Static page titles and small UI strings.
LABEL_TEXTS = {
    "bn": {
        "cover": "কভার",
        "title_page": "শিরোনাম পৃষ্ঠা",
        "info_page": "বই বিষয়ক তথ্য",
        "dedication": "উৎসর্গ",
        "toc": "সূচিপত্র",
        "main_content": "প্রারম্ভ",
        "front_section_prefix": "অন্যান্য",   # "অন্যান্য {idx}"
        "back_section_prefix": "সমাপ্তি",     # "সমাপ্তি {idx}"
        # Nav-only label for uncategorised prose with no explicit heading.
        # The page itself renders with no heading; this text appears in the
        # sidebar / nav only so the reader can still navigate to it.
        "preamble_nav": "পূর্বকথা",
        "html_lang": "bn",
        "epub_lang": "bn",
    },
    "en": {
        "cover": "Cover",
        "title_page": "Title Page",
        "info_page": "Book Information",
        "dedication": "Dedication",
        "toc": "Contents",
        "main_content": "Preface",
        "front_section_prefix": "Others",
        "back_section_prefix": "Appendix",
        # Nav-only label for uncategorised prose with no explicit heading.
        "preamble_nav": "Preliminary Note",
        "html_lang": "en",
        "epub_lang": "en",
    },
}


# Book-info field labels per language. Keys mirror
# ``CANONICAL_BOOK_INFO_KEY_ORDER`` in scraped_book_normalization.py.
BOOK_INFO_LABELS_EN = {
    "title": "Title",
    "original_title": "Original Title",
    "author": "Author",
    "translator": "Translator",
    "editor": "Editor",
    "compiler": "Compiler",
    "illustrator": "Illustrator",
    "cover_artist": "Cover Artist",
    "publisher": "Publisher",
    "other": "Other",
    "type": "Type",
    "series": "Series",
    "category": "Category",
    "first_published": "First Published",
    "publisher_address": "Publisher Address",
    "edition": "Edition",
    "language": "Language",
    "page_count": "Pages",
    "isbn": "ISBN",
    "price": "Price",
}


def labels_for(language):
    return LABEL_TEXTS.get(language) or LABEL_TEXTS["bn"]


_BENGALI_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def to_local_digits(n, language):
    """Return *n* as a string with locale-appropriate digit characters.

    For Bengali (``language == "bn"``), ASCII digits are replaced with
    Bengali numerals (e.g. 1 → ১, 2 → ২).  All other languages keep ASCII.
    """
    s = str(n)
    if language == "bn":
        return s.translate(_BENGALI_DIGITS)
    return s

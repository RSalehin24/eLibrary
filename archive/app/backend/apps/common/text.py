import re
import unicodedata


def clean_display_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


TRAILING_ENTITY_CLOSERS = {
    ")": "(",
    "]": "[",
    "}": "{",
}
ENTITY_EDGE_PUNCTUATION = " \t\r\n-:ঃ–—|/&,;.\"'“”‘’"


def clean_entity_display_text(value):
    cleaned = clean_display_text(value).strip(ENTITY_EDGE_PUNCTUATION)
    if not cleaned:
        return ""

    while cleaned and cleaned[-1] in TRAILING_ENTITY_CLOSERS:
        opener = TRAILING_ENTITY_CLOSERS[cleaned[-1]]
        if cleaned.count(cleaned[-1]) <= cleaned.count(opener):
            break
        cleaned = clean_display_text(cleaned[:-1]).strip(ENTITY_EDGE_PUNCTUATION)

    while cleaned and cleaned[0] in set(TRAILING_ENTITY_CLOSERS.values()):
        closer = next(
            close_char
            for close_char, open_char in TRAILING_ENTITY_CLOSERS.items()
            if open_char == cleaned[0]
        )
        if cleaned.count(cleaned[0]) <= cleaned.count(closer):
            break
        cleaned = clean_display_text(cleaned[1:]).strip(ENTITY_EDGE_PUNCTUATION)

    return cleaned if normalize_catalog_text(cleaned) else ""


def _is_textual_slug_character(char):
    category = unicodedata.category(char)
    return category.startswith(("L", "N", "M"))


def _collapse_separators(value, separator=" "):
    pattern = re.escape(separator) + r"+"
    return re.sub(pattern, separator, value).strip(separator)


def normalize_catalog_text(value):
    if not value:
        return ""

    text = unicodedata.normalize("NFKC", clean_display_text(value)).lower()
    normalized = []
    for char in text:
        if char.isspace():
            normalized.append(" ")
            continue
        if _is_textual_slug_character(char):
            normalized.append(char)

    return _collapse_separators("".join(normalized), " ")


def unicode_slugify(value):
    if not value:
        return ""

    text = unicodedata.normalize("NFKC", clean_display_text(value)).lower()
    slug = []
    previous_was_separator = False

    for char in text:
        if _is_textual_slug_character(char):
            slug.append(char)
            previous_was_separator = False
            continue
        if char in {" ", "-", "_", "/", "|", ":", "–", "—"}:
            if slug and not previous_was_separator:
                slug.append("-")
                previous_was_separator = True

    return _collapse_separators("".join(slug), "-")

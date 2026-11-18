import re

from apps.catalog.models import ContributorRole
from apps.common.text import (
    clean_display_text,
    clean_entity_display_text,
    normalize_catalog_text,
)


ROLE_PATTERNS = {
    ContributorRole.TRANSLATOR: [
        "অনুবাদ",
        "অনুবাদক",
        "ভাষান্তর",
        "রূপান্তর",
        "translation",
        "translator",
    ],
    ContributorRole.COMPILER: ["সংকলক", "সংকলন", "compiled by", "compiler"],
    ContributorRole.EDITOR: [
        "সম্পাদক",
        "সম্পাদনা",
        "সম্পাদনায়",
        "সম্পাদনায়",
        "সম্পাদ",
        "সম্পাদিত",
        "editor",
        "edited by",
    ],
    ContributorRole.COVER_ARTIST: [
        "প্রচ্ছদ-শিল্পী",
        "প্রচ্ছদ শিল্পী",
        "প্রচ্ছদ ফটো",
        "প্রচ্ছদ",
        "cover artist",
        "cover photo",
        "cover",
    ],
    ContributorRole.ILLUSTRATOR: ["অলংকরণ", "illustration"],
    ContributorRole.PUBLISHER: [
        "প্রকাশক",
        "প্রকাশনী",
        "প্রকাশন",
        "publisher",
        "published by",
    ],
}

FRONT_MATTER_PATTERNS = {
    "first_published": ["প্রথম প্রকাশ", "প্রকাশকাল", "প্রকাশিত", "first published", "published", "publication"],
    "original_title": ["মূল", "original title"],
    "language": ["ভাষা", "language"],
    "publisher_address": [
        "প্রকাশনার ঠিকানা",
        "প্রকাশকের ঠিকানা",
        "প্রকাশনীর ঠিকানা",
        "ঠিকানা",
        "publisher address",
        "address",
    ],
    "series": ["সিরিজ", "ধারাবাহিক", "series"],
    "type": ["ধরন", "ধরণ", "প্রকার", "type", "genre"],
    "category": ["শ্রেণি", "শ্রেণী", "বিভাগ", "category"],
    "isbn": ["isbn", "আইএসবিএন"],
    "price": ["মূল্য", "দাম", "price"],
    "page_count": [
        "বইয়ের পাতার সংখ্যা",
        "বইয়ের পাতার সংখ্যা",
        "পাতার সংখ্যা",
        "পৃষ্ঠা সংখ্যা",
        "page count",
        "pages",
    ],
    "edition": [
        "প্রথম সংস্করণ",
        "দ্বিতীয় সংস্করণ",
        "দ্বিতীয় সংস্করণ",
        "তৃতীয় সংস্করণ",
        "তৃতীয় সংস্করণ",
        "পরিবর্ধিত সংস্করণ",
        "সংস্করণ",
        "first edition",
        "second edition",
        "third edition",
        "edition",
    ],
}

MAX_CONTRIBUTOR_NAME_WORDS = 8
MAX_CONTRIBUTOR_NAME_LENGTH = 80
CONTRIBUTOR_CONNECTOR_PATTERN = re.compile(r"\s+(?:ও|and|&)\s+", re.IGNORECASE)
CONTRIBUTOR_INITIAL_TOKEN_PATTERN = re.compile(r"^(?:[A-Za-z\u0980-\u09FF]{1,4}\.)+$")
ROLE_SEGMENT_SPLIT_PATTERN = re.compile(r"\s*(?:(?<!\d)/(?!\d)|\||\n)\s*")
LEADING_CONTRIBUTOR_HELPER_PATTERN = re.compile(
    r"^(?:করেছেন|কর্তৃক|দ্বারা|by)\b\s*[:ঃ\-–—]?\s*",
    re.IGNORECASE,
)
TRAILING_CONTRIBUTOR_HELPER_PATTERN = re.compile(
    r"\s*(?:করেছেন|কর্তৃক|দ্বারা|by)\s*$",
    re.IGNORECASE,
)
NON_PERSON_TITLE_WORDS = {
    "খণ্ড",
    "পর্ব",
    "অধ্যায়",
    "অধ্যায়",
    "অনুবাদ",
    "অক্ষরবিন্যাস",
    "বর্ণ",
    "সংকলন",
    "সংস্করণ",
    "সংশোধন",
    "ডেস্ক",
    "edition",
    "volume",
    "part",
    "series",
    "সমগ্র",
    "বিভাগ",
    "সদস্য",
    "সচিব",
    "সভাপতি",
    "পরিচালক",
    "পরিষদ",
    "গল্প",
    "ছোটগল্প",
    "উপন্যাস",
    "প্রবন্ধ",
    "কাহিনি",
    "কাহিনী",
    "সাহিত্য",
    "ইতিহাস",
    "দর্শন",
}
NON_NAME_PHRASE_WORDS = {
    "হোক",
    "হওক",
    "নির্ভর",
    "অসাধারণ",
    "বহুল",
    "পঠিত",
    "পাতা",
    "পাতার",
    "মণিমুক্তো",
    "তুলে",
    "আনাই",
    "সব্যসাচী",
    "ভালো",
    "লাগবে",
    "কৃতজ্ঞতার",
    "শেষ",
    "নেই",
}
ENGLISH_PROSE_FRAGMENT_WORDS = {
    "and",
    "book",
    "books",
    "chapter",
    "chapters",
    "content",
    "contents",
    "elaborate",
    "foreword",
    "novel",
    "novels",
    "preface",
    "purports",
    "reader",
    "readers",
    "story",
    "text",
    "texts",
}
ADDRESS_FRAGMENT_WORDS = {
    "বাংলাদেশ",
    "ঢাকা",
    "কলকাতা",
    "খুলনা",
    "সড়ক",
    "সড়ক",
    "রোড",
    "road",
    "row",
    "street",
    "avenue",
    "সেগুনবাগিচা",
    "bangladesh",
    "dhaka",
    "kolkata",
    "khulna",
    "chittagong",
    "chattogram",
    "sylhet",
}
PUBLISHER_ORGANIZATION_KEYWORDS = {
    "প্রকাশনী",
    "প্রকাশন",
    "পাবলিশার্স",
    "পাবলিশারস",
    "পাবলিশিং",
    "publishers",
    "publisher",
    "publishing",
    "লাইব্রেরী",
    "লাইব্রেরি",
    "library",
    "প্রাইভেট",
    "লিমিটেড",
    "limited",
}
LEADING_ROLE_DESCRIPTOR_PATTERN = re.compile(
    r"^(?:শিল্পী|ফটো|photo|artist)\s*[:ঃ\-–—]?\s*",
    re.IGNORECASE,
)
POTENTIAL_METADATA_BOUNDARY_PATTERN = re.compile(r"\s{2,}|\s+(?=[A-Za-z\u0980-\u09FF])")
ROLE_LABEL_HELPER_PATTERN = re.compile(r"\b(?:করেছেন|কর্তৃক|দ্বারা|by)\b", re.IGNORECASE)
PUBLISHER_STOP_PATTERN = re.compile(
    r"(?:[।.]|;|,?\s+at\s+\d|,?\s+(?:printed at|first edition|price)\b|,?\s+(?:প্রথম প্রকাশ|প্রকাশকাল)\b)",
    re.IGNORECASE,
)
TRAILING_ADDRESS_INTRO_PATTERN = re.compile(r"\s+(?:at|ঠিকানা)\s*$", re.IGNORECASE)
ALLOWED_COLON_NAME_PREFIX_PATTERN = re.compile(r"^(?:মো[:ঃ])\s*", re.IGNORECASE)
LOWERCASE_LATIN_FRAGMENT_PATTERN = re.compile(r"^[a-z][a-z\s'’.-]*$")
BANGLA_TEXT_PATTERN = re.compile(r"[\u0980-\u09FF]")
INCOMPLETE_NAME_TOKENS = {
    "মো",
    "মোঃ",
    "মো:",
    "md",
    "md.",
    "mohd",
    "mohd.",
}
ENGLISH_BYLINE_PATTERN = re.compile(r"^(?P<title>.+?)\s+by\s+(?P<name>.+)$", re.IGNORECASE)
ENGLISH_BYLINE_ROLE_PREFIXES = {
    "compiled",
    "edited",
    "illustrated",
    "published",
    "translated",
    "written",
}

# Tokens that, when they appear as the first token of a contributor candidate,
# indicate the value is a sentence fragment, role descriptor, dedication, or
# pronoun-led clause — never a person's name.
# NOTE: role-label words like "অনুবাদক", "ভূমিকা", "প্রচ্ছদ", "প্রকাশ" are
# intentionally NOT in this set: the front-matter parser already splits them
# from values via the colon-separator, and some test placeholders legitimately
# create contributors whose names begin with these labels (e.g. "অনুবাদক এক").
LEADING_NON_NAME_BENGALI_TOKENS = {
    "ও", "এবং", "অথবা", "কিন্তু",
    "সম্পাদনা",
    "কবিতা", "সহযোগী",
    # Collaboration / courtesy prefix words that introduce the actual name
    # (e.g. "সহযোগিতায় – অয়ন বন্দ্যোপাধ্যায়"). The raw string with the prefix
    # is noise; the name after the dash is captured separately by
    # clean_contributor_value via COLLABORATION_PREFIX_PATTERN.
    "সহযোগিতায়", "সহায়তায়", "সহকারে", "সৌজন্যে",
    "প্রসঙ্গে", "সম্পর্কে", "পরিচিতি",
    "উৎসর্গ",
    "প্রধান", "সরকারি", "বিভাগীয়",
    "কিতাব", "পরিমার্জন",
    "আমি", "তুমি", "তোমার", "আমার", "আমরা", "তোমরা",
    "কোথায়", "কী", "কি", "কে", "যে", "যা", "যদি", "তা", "তাই", "সব",
    "থেকে",
    "করতে", "করব", "করল", "করলে", "করিয়ে", "করে",
    "করেছিল", "করেছিলেন", "করেছেন", "করছেন", "করছে",
    "করলেন", "ছেপেছেন",
    # Academic / honorific titles that lead a credential phrase rather
    # than a name (e.g. "অধ্যাপক রহমান", "ডক্টর হাসান") — when these lead,
    # the actual person name (if any) is captured separately elsewhere.
    "অধ্যাপক", "অধ্যাপিকা", "অধ্যক্ষ", "অধ্যক্ষা",
    "শিক্ষক", "শিক্ষিকা", "প্রিন্সিপাল",
    "ডক্টর", "ডঃ", "ডা", "ডা.", "ডাঃ",
    "জনাব", "মৌলভী", "মৌলানা",
    # Place / date intros that prefix biographical lines.
    "জন্ম", "মৃত্যু", "প্রয়াত", "জন্মস্থান",
    # Common publication-metadata leads.
    "প্রথম", "দ্বিতীয়", "তৃতীয়",
    "মূল্য", "দাম", "মুদ্রক",
}

ENGLISH_LEADING_NON_NAME_TOKENS = {
    "by", "of", "and", "the", "from", "with", "for", "to",
    "at", "in", "on", "as", "is", "are", "was", "were", "an", "a",
}

# Bengali single-word values that are never a person's name even though they
# have Bengali characters and pass other heuristics.
BENGALI_NON_NAME_STANDALONE_WORDS = {
    "উৎসর্গ", "প্রসঙ্গে", "সম্পর্কে", "পরিচিতি",
    "সম্পাদনা", "সম্পাদনায়", "ভূমিকা", "প্রচ্ছদ",
    "অনুবাদ", "অনুবাদক", "প্রকাশ", "মুদ্রণ", "সংস্করণ",
    "কবিতা", "সহযোগী",
    "কলিকাতা", "অধ্যাপক",
    "কিতাব", "পরিমার্জন",
    "গপ্পো-সপ্পো",
}

# Single English topical/genre words frequently mis-captured as translator
# or author values. Only applied when the candidate is fully Latin script
# with <=2 tokens.
ENGLISH_TOPIC_NOISE_WORDS = {
    "horror", "fiction", "comedy", "drama", "sigma", "thriller",
    "mystery", "romance", "adventure", "nonfiction", "biography",
    "categorie", "categories", "essay", "essays", "stories", "story",
    "short",
}

# High-confidence Bengali verb-form suffixes (length >= 3). If any token in
# the candidate ends in one of these, the value is a sentence fragment.
BENGALI_VERB_SUFFIXES = (
    "ছেন", "ছিলেন", "চ্ছে", "চ্ছেন", "চ্ছি",
    "েছিলেন", "েছিলো", "েছিল", "েছেন", "েছে",
    "াচ্ছা", "বেন",
)

# Explicit Bengali verb tokens whose suffixes are too short to detect safely
# but which never appear as parts of a person's name.
BENGALI_VERB_TOKENS = {
    "করছে", "করছেন", "করল", "করলে", "করলেন",
    "করিয়ে", "করেছিল", "করেছিলেন", "করেছেন",
    "জানালো", "জিজ্ঞেস", "যাচ্ছা", "যাচ্ছি", "যাচ্ছেন",
    "বলছে", "বলছেন", "চলছে", "চলছেন",
    "এসেছে", "এসেছেন", "গেছে", "গেছেন",
    "দাঁড়ায়", "ছেপেছেন", "বেরোচ্ছে", "জানতে",
    "চাইবেন", "নেবেন", "ফেলেছেন",
}

LEADING_QUOTE_OR_BULLET_PATTERN = re.compile(
    r"^[\s\u00a0]*[•·●◦▪◾◽⬛⬜“”‘’\"'`‚„«»]+\s*"
)
TRAILING_PARENTHETICAL_PATTERN = re.compile(r"\s*\([^()]*\)\s*$")
ORPHAN_TRAILING_PAREN_PATTERN = re.compile(r"\)+\s*$")


# Strip "সহযোগিতায় – " (in-collaboration-with) style prefixes so the actual
# contributor name is validated rather than the prefix phrase.
COLLABORATION_PREFIX_PATTERN = re.compile(
    r"^(?:সহযোগিতায়|সহায়তায়|সহকারে|সৌজন্যে)\s*[-\u2013\u2014:]\s*",
    re.IGNORECASE,
)

# Bengali/Gregorian calendar month names.
# A standalone month name is NEVER a valid contributor or publisher name.
BENGALI_MONTH_NAMES = frozenset({
    "জানুয়ারি", "জানুয়ারী",
    "ফেব্রুয়ারি", "ফেব্রুয়ারী",
    "মার্চ",
    "এপ্রিল",
    "মে",
    "জুন",
    "জুলাই",
    "আগস্ট", "আগষ্ট",
    "সেপ্টেম্বর", "সেপ্টেম্বার",
    "অক্টোবর", "অক্টোবার",
    "নভেম্বর", "নভেম্বার",
    "ডিসেম্বর", "ডিসেম্বার",
    # Bengali calendar months
    "বৈশাখ", "জ্যৈষ্ঠ", "আষাঢ়", "শ্রাবণ", "ভাদ্র", "আশ্বিন",
    "কার্তিক", "অগ্রহায়ণ", "পৌষ", "মাঘ", "ফাল্গুন", "চৈত্র",
})



def _strip_leading_quote_or_bullet(value):
    cleaned = value
    while True:
        next_value = LEADING_QUOTE_OR_BULLET_PATTERN.sub("", cleaned, count=1)
        if next_value == cleaned:
            return cleaned.strip()
        cleaned = next_value


def _strip_trailing_parens(value):
    cleaned = value.strip()
    while TRAILING_PARENTHETICAL_PATTERN.search(cleaned):
        cleaned = TRAILING_PARENTHETICAL_PATTERN.sub("", cleaned).rstrip()
    if "(" not in cleaned:
        cleaned = ORPHAN_TRAILING_PAREN_PATTERN.sub("", cleaned).rstrip()
    return cleaned


def build_metadata_label_aliases():
    aliases = []
    for role, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            aliases.append({"alias": clean_display_text(pattern), "key": role, "role": role})
    aliases.extend(
        [
            {
                "alias": "অনুবাদ ও সম্পাদনা",
                "key": ContributorRole.TRANSLATOR,
                "role": ContributorRole.TRANSLATOR,
            },
            {
                "alias": "ভাষান্তর ও সম্পাদনা",
                "key": ContributorRole.TRANSLATOR,
                "role": ContributorRole.TRANSLATOR,
            },
            {
                "alias": "রূপান্তর ও সম্পাদনা",
                "key": ContributorRole.TRANSLATOR,
                "role": ContributorRole.TRANSLATOR,
            },
            {
                "alias": "প্রচ্ছদ ও অলংকরণ",
                "key": ContributorRole.COVER_ARTIST,
                "role": ContributorRole.COVER_ARTIST,
            },
        ]
    )
    for key, patterns in FRONT_MATTER_PATTERNS.items():
        for pattern in patterns:
            aliases.append({"alias": clean_display_text(pattern), "key": key, "role": ""})
    return sorted(aliases, key=lambda item: len(item["alias"]), reverse=True)


METADATA_LABEL_ALIASES = build_metadata_label_aliases()
ALL_METADATA_LABELS = [entry["alias"] for entry in METADATA_LABEL_ALIASES]
CONTRIBUTOR_ROLE_LABELS = {
    normalize_catalog_text(entry["alias"])
    for entry in METADATA_LABEL_ALIASES
    if entry["role"]
}
CONTRIBUTOR_ROLE_ALIASES = [entry for entry in METADATA_LABEL_ALIASES if entry["role"]]
MIDSTRING_ROLE_LABELS = {
    normalize_catalog_text(entry["alias"])
    for entry in CONTRIBUTOR_ROLE_ALIASES
    if normalize_catalog_text(entry["alias"]).endswith(" by")
}
PUBLISHER_NON_NAME_WORDS = {
    "বইমেলা",
    # Collaboration prefix words — never a publisher name.
    "সহযোগিতায়", "সহায়তায়", "সহকারে", "সৌজন্যে",
    "বইয়ের",
    "বইয়ের",
    "ভাষা",
    "পাতা",
    "পাতার",
    "প্রকাশকাল",
    "সংখ্যা",
    "সন",
    "edition",
    "first edition",
    "language",
    "page",
    "pages",
    "price",
    "printed",
    "press",    "date",
    "date of",
    "of",
    "and",
    "the",
    "by",
    "at",
    "in",
    "from",
    "to",
}
# Single-token English words (case-insensitive, normalized) that are never a
# valid standalone publisher name even when they pass other heuristics. This
# catches address tails and noise tokens like "Dhaka", "Md", "Mitra" appearing
# alone without a publishing organisation keyword.
PUBLISHER_DISALLOWED_SOLO_ENGLISH = {
    "md",
    "mr",
    "mrs",
    "ms",
    "dr",
    "mitra",
    "kumar",
    "das",
    "roy",
    "sen",
    "lal",
    "chand",
    "mohd",
    "smt",
    "shri",}
EXPLICIT_SEPARATOR_ONLY_LABELS = {
    normalize_catalog_text("মূল"),
}


def canonical_role(role):
    if role == ContributorRole.COMPILER:
        return ContributorRole.EDITOR
    return role or ""


def roles_in_text(text):
    normalized = normalize_catalog_text(text)
    if not normalized:
        return []

    roles = []
    for role, patterns in ROLE_PATTERNS.items():
        if any(role_pattern_matches(normalized, normalize_catalog_text(pattern)) for pattern in patterns):
            roles.append(role)
    return roles


def role_pattern_matches(normalized_text, normalized_pattern):
    if not normalized_text or not normalized_pattern:
        return False
    return (
        normalized_text == normalized_pattern
        or normalized_text.startswith(f"{normalized_pattern} ")
        or normalized_text.endswith(f" {normalized_pattern}")
        or f" {normalized_pattern} " in normalized_text
    )


def contains_publisher_keyword(value):
    normalized = normalize_catalog_text(value)
    return any(
        normalize_catalog_text(keyword) in normalized
        for keyword in PUBLISHER_ORGANIZATION_KEYWORDS
    )


def looks_like_address_fragment(value):
    cleaned = clean_display_text(value)
    normalized = normalize_catalog_text(cleaned)
    if not normalized:
        return False
    if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", cleaned):
        return True
    if any(normalize_catalog_text(word) in normalized for word in ADDRESS_FRAGMENT_WORDS):
        return True
    if re.search(r"\b\d{3,}\b", cleaned) and len(cleaned.split()) <= 3:
        return True
    if re.search(r"\b\d+(?:/\d+)?\b", cleaned) and len(cleaned.split()) >= 4:
        return True
    # Bengali-numeral street fragments such as "৩৮/২ক" or "১২/খ".
    # An entire short chunk that is mostly Bengali digits + a slash/letter is an
    # address number, never a person or organisation name.
    digit_chars = re.findall(r"[০-৯]", cleaned)
    if digit_chars and len(cleaned.split()) <= 2:
        non_space = [ch for ch in cleaned if not ch.isspace()]
        digit_like = re.findall(r"[০-৯0-9/ক-হ়া-্]", cleaned)
        if len(digit_chars) >= 2 and len(non_space) <= 6:
            return True
        # Pattern like "৩৮/২ক" — digits, optional slash, single Bengali letter.
        if re.fullmatch(r"[০-৯]+(?:/[০-৯]+)?[ক-হ]?", cleaned.strip()):
            return True
    return False


def split_multi_value(value):
    if not value:
        return []
    chunks = re.split(r"[,;|\n]+", value)
    deduped = []
    seen = set()
    for chunk in chunks:
        cleaned = clean_entity_display_text(chunk)
        normalized = normalize_catalog_text(cleaned)
        if not cleaned or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(cleaned)
    return deduped


def clean_contributor_value(value):
    cleaned = clean_entity_display_text(value)
    if not cleaned:
        return ""

    while True:
        next_value = LEADING_CONTRIBUTOR_HELPER_PATTERN.sub("", cleaned, count=1)
        if next_value == cleaned:
            break
        cleaned = next_value
    while True:
        next_value = LEADING_ROLE_DESCRIPTOR_PATTERN.sub("", cleaned, count=1)
        if next_value == cleaned:
            break
        cleaned = next_value
    cleaned = TRAILING_CONTRIBUTOR_HELPER_PATTERN.sub("", cleaned)
    cleaned = _strip_leading_quote_or_bullet(cleaned)
    cleaned = _strip_trailing_parens(cleaned)
    # Strip "সহযোগিতায় – " / "সহায়তায় – " prefix phrases so the actual name is extracted.
    while True:
        next_value = COLLABORATION_PREFIX_PATTERN.sub("", cleaned, count=1)
        if next_value == cleaned:
            break
        cleaned = next_value
    return clean_entity_display_text(cleaned)


def has_non_name_phrase_marker(value):
    normalized_tokens = set(normalize_catalog_text(value).split())
    return bool(
        normalized_tokens
        & {normalize_catalog_text(word) for word in NON_NAME_PHRASE_WORDS}
    )


def has_english_prose_marker(value):
    return bool(set(normalize_catalog_text(value).split()) & ENGLISH_PROSE_FRAGMENT_WORDS)


def looks_like_english_prose_fragment(value):
    cleaned = clean_display_text(value)
    if not cleaned or BANGLA_TEXT_PATTERN.search(cleaned):
        return False
    if not LOWERCASE_LATIN_FRAGMENT_PATTERN.fullmatch(cleaned):
        return False
    tokens = normalize_catalog_text(cleaned).split()
    if len(tokens) < 2:
        return False
    if tokens[0] in {"and", "or", "the", "a", "an"}:
        return True
    return bool(set(tokens) & ENGLISH_PROSE_FRAGMENT_WORDS)


def looks_like_contributor_name(value, role=""):
    cleaned = clean_entity_display_text(value)
    if not cleaned:
        return False
    # Strip leading bullets/quotes; they never lead a person's name.
    cleaned = _strip_leading_quote_or_bullet(cleaned)
    # Strip trailing balanced `(...)` annotation blocks and orphan `)`.
    cleaned = _strip_trailing_parens(cleaned)
    if not cleaned:
        return False
    if normalize_catalog_text(cleaned.strip(".:ঃ")) in INCOMPLETE_NAME_TOKENS:
        return False
    if role != ContributorRole.PUBLISHER and re.search(r"[0-9০-৯]", cleaned):
        return False
    # Reject very short values that cannot be a real name (e.g. জে, বি).
    if len(cleaned.replace(" ", "")) < 3:
        return False
    # Reject standalone Bengali month names and date expressions for ALL roles.
    _month_norms = {normalize_catalog_text(m) for m in BENGALI_MONTH_NAMES}
    _norm_for_month = normalize_catalog_text(cleaned)
    if _norm_for_month in _month_norms:
        return False
    _norm_tokens = _norm_for_month.split()
    if (
        len(_norm_tokens) == 2
        and _norm_tokens[1] in _month_norms
        and re.fullmatch(r"[০-৯0-9]+", _norm_tokens[0])
    ):
        return False
    if re.search(r"[।!?]", cleaned):
        return False
    if (
        role != ContributorRole.PUBLISHER
        and any(separator in cleaned for separator in (":", "ঃ"))
        and not ALLOWED_COLON_NAME_PREFIX_PATTERN.match(cleaned)
    ):
        return False
    if looks_like_address_fragment(cleaned):
        return False
    normalized = normalize_catalog_text(cleaned)
    if normalized.isdigit():
        return False
    normalized_tokens = set(normalized.split())
    if normalized_tokens & {normalize_catalog_text(word) for word in NON_PERSON_TITLE_WORDS}:
        return False
    if role != ContributorRole.PUBLISHER and has_non_name_phrase_marker(cleaned):
        return False
    if role != ContributorRole.PUBLISHER and has_english_prose_marker(cleaned):
        return False
    if role != ContributorRole.PUBLISHER and looks_like_english_prose_fragment(cleaned):
        return False
    if role and role != ContributorRole.PUBLISHER and is_role_label_text(cleaned):
        return False
    if role != ContributorRole.PUBLISHER and contains_publisher_keyword(cleaned):
        return False

    # New (post-2024-11) rejection rules for persisted-bad-row corpus.
    if role != ContributorRole.PUBLISHER:
        # Reject standalone Bengali non-name single words (dedications,
        # role labels, postpositions, cities).
        bengali_standalone = {
            normalize_catalog_text(w) for w in BENGALI_NON_NAME_STANDALONE_WORDS
        }
        if normalized in bengali_standalone:
            return False
        # Reject single/two-token English candidates that are pure topical
        # noise (`Horror`, `Short Stories`, `Sigma`).
        if not BANGLA_TEXT_PATTERN.search(cleaned) and len(cleaned.split()) <= 2:
            topic_norms = {
                normalize_catalog_text(w) for w in ENGLISH_TOPIC_NOISE_WORDS
            }
            if set(normalized.split()) & topic_norms:
                return False
        tokens = cleaned.split()
        if tokens:
            first_token_norm = normalize_catalog_text(tokens[0])
            leading_bad_bn = {
                normalize_catalog_text(w) for w in LEADING_NON_NAME_BENGALI_TOKENS
            }
            if first_token_norm in leading_bad_bn:
                return False
            leading_bad_en = {
                normalize_catalog_text(w) for w in ENGLISH_LEADING_NON_NAME_TOKENS
            }
            if first_token_norm in leading_bad_en:
                return False
            # Reject any token ending in a high-confidence Bengali verb suffix.
            for tok in tokens:
                tok_norm = normalize_catalog_text(tok)
                if any(tok_norm.endswith(suf) for suf in BENGALI_VERB_SUFFIXES):
                    return False
            # Reject any token that matches an explicit Bengali verb form.
            verb_tokens_norm = {
                normalize_catalog_text(w) for w in BENGALI_VERB_TOKENS
            }
            if {normalize_catalog_text(tok) for tok in tokens} & verb_tokens_norm:
                return False
    if role == ContributorRole.PUBLISHER:
        publisher_non_name_tokens = {
            normalize_catalog_text(word)
            for word in PUBLISHER_NON_NAME_WORDS
            if " " not in normalize_catalog_text(word)
        }
        publisher_non_name_phrases = {
            normalize_catalog_text(word)
            for word in PUBLISHER_NON_NAME_WORDS
            if " " in normalize_catalog_text(word)
        }
        if normalized_tokens & publisher_non_name_tokens or any(
            phrase in normalized for phrase in publisher_non_name_phrases
        ):
            return False
        # Reject standalone English tokens that are never a publisher name on
        # their own (honorifics, common surnames/first-names, address tails)
        # unless paired with a publishing organisation keyword.
        if (
            not BANGLA_TEXT_PATTERN.search(cleaned)
            and not contains_publisher_keyword(cleaned)
        ):
            disallowed = {
                normalize_catalog_text(word)
                for word in PUBLISHER_DISALLOWED_SOLO_ENGLISH
            }
            if normalized_tokens & disallowed:
                return False
            # Require at least 2 tokens of >=2 chars OR a single token of
            # >=4 chars for a bare English publisher candidate.
            english_tokens = [t for t in normalized.split() if t]
            if len(english_tokens) == 1 and len(english_tokens[0]) < 4:
                return False
    if (
        role == ContributorRole.PUBLISHER
        and len(cleaned.split()) > 4
        and not contains_publisher_keyword(cleaned)
    ):
        return False
    for token in cleaned.split():
        normalized_token = token.strip("()[]{}\"'“”‘’,;:-")
        if "." not in normalized_token:
            continue
        if CONTRIBUTOR_INITIAL_TOKEN_PATTERN.fullmatch(normalized_token):
            continue
        return False
    if len(cleaned) > MAX_CONTRIBUTOR_NAME_LENGTH:
        return False
    if len(cleaned.split()) > MAX_CONTRIBUTOR_NAME_WORDS:
        return False
    return bool(normalized)


def trim_publisher_candidate(chunk):
    cleaned = clean_display_text(chunk)
    if not cleaned:
        return []

    stop_match = PUBLISHER_STOP_PATTERN.search(cleaned)
    if stop_match and stop_match.start() > 0:
        cleaned = clean_display_text(cleaned[: stop_match.start()])

    address_match = re.search(r"\b\d+(?:/\d+)?\b", cleaned)
    if address_match and address_match.start() > 0:
        cleaned = clean_display_text(cleaned[: address_match.start()])

    cleaned = clean_display_text(TRAILING_ADDRESS_INTRO_PATTERN.sub("", cleaned))
    if not cleaned or looks_like_address_fragment(cleaned):
        return []

    tokens = cleaned.split()
    normalized_tokens = [normalize_catalog_text(token.strip(",:;")) for token in tokens]
    organization_index = -1
    for index, token in enumerate(normalized_tokens):
        if token in {normalize_catalog_text(word) for word in PUBLISHER_ORGANIZATION_KEYWORDS}:
            organization_index = index
            break

    if organization_index <= 0:
        return [cleaned]

    organization_start = max(0, organization_index - 1)
    human_prefix = clean_display_text(" ".join(tokens[:organization_start]))
    organization_name = clean_display_text(" ".join(tokens[organization_start:]))

    candidates = []
    if human_prefix:
        candidates.append(human_prefix)
    if organization_name:
        candidates.append(organization_name)
    return candidates or [cleaned]


def split_contributor_chunks(value, role=""):
    chunks = []
    seen = set()
    canonical = canonical_role(role)
    cleaned_value = clean_contributor_value(value)
    if canonical == ContributorRole.PUBLISHER:
        stop_match = PUBLISHER_STOP_PATTERN.search(cleaned_value)
        if stop_match and stop_match.start() > 0:
            cleaned_value = clean_display_text(cleaned_value[: stop_match.start()])

    publisher_raw_chunks = (
        split_multi_value(cleaned_value)
        if canonical == ContributorRole.PUBLISHER
        else []
    )
    # When a publisher value is comma-separated and at least one chunk
    # contains an organisation keyword, the line is almost always shaped
    # "<proprietor>, <publisher org>, <street>, <area>, <city>". Keep only
    # the org-keyword chunks; drop proprietor and address tails. Without a
    # keyword anywhere, fall back to the legacy per-chunk handling so that
    # single-name publishers like "Penguin" still survive.
    publisher_keep_only_keyword_chunks = (
        canonical == ContributorRole.PUBLISHER
        and len(publisher_raw_chunks) > 1
        and any(contains_publisher_keyword(c) for c in publisher_raw_chunks)
    )

    for chunk in split_multi_value(cleaned_value):
        if canonical == ContributorRole.PUBLISHER:
            if publisher_keep_only_keyword_chunks and not contains_publisher_keyword(chunk):
                continue
            raw_candidates = trim_publisher_candidate(chunk)
        else:
            raw_candidates = [chunk]

        for raw_candidate in raw_candidates:
            expanded = [
                clean_entity_display_text(part)
                for part in CONTRIBUTOR_CONNECTOR_PATTERN.split(raw_candidate)
                if clean_entity_display_text(part)
            ]
            if canonical == ContributorRole.PUBLISHER and len(expanded) > 1:
                if not all(contains_publisher_keyword(part) for part in expanded):
                    continue
            candidates = (
                expanded
                if len(expanded) > 1
                and all(looks_like_contributor_name(part, role=canonical) for part in expanded)
                else [raw_candidate]
            )

            for candidate in candidates:
                normalized = normalize_catalog_text(candidate)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                chunks.append(candidate)

    return chunks


def split_contributor_value(value, role=""):
    chunks = split_contributor_chunks(value, role=role)
    if not chunks:
        return []
    return [chunk for chunk in chunks if looks_like_contributor_name(chunk, role=role)]


def metadata_label_matches(text):
    cleaned = clean_display_text(text)
    matches = []

    for entry in METADATA_LABEL_ALIASES:
        alias = entry["alias"]
        pattern = re.compile(rf"{re.escape(alias)}(?P<suffix>\s*(?:[:ঃ]\s*|[-–—]\s*|\s+))", re.IGNORECASE)
        for match in pattern.finditer(cleaned):
            start_index = match.start()
            end_index = start_index + len(alias)
            prefix = cleaned[:start_index].rstrip()
            suffix = match.group("suffix") or ""
            alias_normalized = normalize_catalog_text(alias)
            if normalize_catalog_text(alias) in EXPLICIT_SEPARATOR_ONLY_LABELS and suffix.isspace():
                continue
            if start_index > 0 and re.match(r"[A-Za-z0-9_\u0980-\u09FF]", cleaned[start_index - 1]):
                continue
            if end_index < len(cleaned) and re.match(r"[A-Za-z0-9_\u0980-\u09FF]", cleaned[end_index]):
                continue
            if prefix and suffix.isspace() and alias_normalized not in MIDSTRING_ROLE_LABELS:
                continue
            if prefix and not prefix.endswith(("-", "–", "—", ":", "ঃ", "|", "/", ",", ";")):
                stripped_suffix = suffix.strip()
                if (
                    stripped_suffix not in {":", "ঃ", "-", "–", "—"}
                    and alias_normalized not in MIDSTRING_ROLE_LABELS
                ):
                    continue
            if prefix.rstrip().endswith((":", "ঃ")) and suffix.isspace():
                continue
            matches.append(
                {
                    "start": start_index,
                    "end": match.end(),
                    "alias": alias,
                    "role": entry["role"],
                }
            )

    deduped = []
    covered_until = -1
    for match in sorted(matches, key=lambda item: (item["start"], -(item["end"] - item["start"]))):
        if match["start"] < covered_until:
            continue
        deduped.append(match)
        covered_until = max(covered_until, match["end"])
    return deduped


def normalized_role_label_text(text):
    cleaned = clean_display_text(text)
    if not cleaned:
        return ""
    cleaned = ROLE_LABEL_HELPER_PATTERN.sub(" ", cleaned)
    cleaned = clean_display_text(cleaned.strip(" -:ঃ|/"))
    return normalize_catalog_text(cleaned)


def is_role_label_text(text):
    normalized = normalized_role_label_text(text)
    return bool(normalized and normalized in CONTRIBUTOR_ROLE_LABELS)


def split_metadata_fragments(text):
    cleaned = clean_display_text(text)
    if not cleaned:
        return []

    matches = metadata_label_matches(cleaned)
    fragments = []

    if matches:
        first_start = matches[0]["start"]
        leading_fragment = clean_display_text(cleaned[:first_start])
        if leading_fragment:
            leading_evidence = extract_contributor_evidence(
                leading_fragment,
                raw_value=leading_fragment,
            )
            if leading_evidence["contributors"] or leading_evidence["authors"]:
                fragments.append(leading_fragment)

        for index, match in enumerate(matches):
            next_start = matches[index + 1]["start"] if index + 1 < len(matches) else len(cleaned)
            fragment = clean_display_text(cleaned[match["start"] : next_start].strip(" -–—|/"))
            if fragment:
                fragments.append(fragment)
        return fragments

    return [cleaned]


def parse_role_labeled_segment(segment):
    cleaned = clean_display_text(segment)
    if not cleaned:
        return [], []

    for entry in CONTRIBUTOR_ROLE_ALIASES:
        alias = entry["alias"]
        for separator_pattern in (r"\s*(?:[:ঃ]|[-–—])\s*", r"\s+"):
            match = re.match(
                rf"^{re.escape(alias)}(?:\s+(?:করেছেন|কর্তৃক|দ্বারা|by))*{separator_pattern}(?P<value>.+)$",
                cleaned,
                re.IGNORECASE,
            )
            if not match:
                continue
            roles = roles_in_text(alias) or [entry["role"]]
            names = split_contributor_value(
                clean_contributor_value(match.group("value")),
                role=canonical_role(roles[0]),
            )
            if names:
                return roles, names

    suffix_match = re.match(r"^(?P<value>.+?)\s+(?P<label>সম্পাদিত)\s*$", cleaned)
    if suffix_match:
        return [ContributorRole.EDITOR], split_contributor_value(
            clean_contributor_value(suffix_match.group("value")),
            role=ContributorRole.EDITOR,
        )

    byline_match = ENGLISH_BYLINE_PATTERN.match(cleaned)
    if byline_match:
        title_prefix = clean_display_text(byline_match.group("title"))
        normalized_prefix_tokens = normalize_catalog_text(title_prefix).split()
        if (
            title_prefix
            and not (
                len(normalized_prefix_tokens) == 1
                and normalized_prefix_tokens[0] in ENGLISH_BYLINE_ROLE_PREFIXES
            )
        ):
            names = split_contributor_value(
                clean_contributor_value(byline_match.group("name")),
                role=ContributorRole.AUTHOR,
            )
            if names:
                return [ContributorRole.AUTHOR], names

    return [], []


def extract_contributor_evidence(text, default_roles=None, raw_value=""):
    default_roles = [role for role in default_roles or [] if role]
    # Strip trailing list separators ( , ; । etc.) from the raw_value so
    # callers downstream don't see noisy values like "প্রথমা,".
    canonical_raw_value = (raw_value or text or "").strip().rstrip(",;।:.ঃ–—- ").strip()
    authors = []
    contributors = []
    seen_author_names = set()
    seen_role_names = set()

    fragments = [clean_display_text(text)] if default_roles else split_metadata_fragments(text)
    for fragment in fragments:
        for segment in ROLE_SEGMENT_SPLIT_PATTERN.split(clean_display_text(fragment)):
            cleaned_segment = clean_display_text(segment)
            if not cleaned_segment:
                continue

            roles, names = (
                ([], [])
                if default_roles
                else parse_role_labeled_segment(cleaned_segment)
            )
            if roles and names:
                for role in roles:
                    role = canonical_role(role)
                    for name in names:
                        role_key = (role, normalize_catalog_text(name))
                        if role_key in seen_role_names:
                            continue
                        seen_role_names.add(role_key)
                        contributors.append(
                            {
                                "name": name,
                                "role": role,
                                "raw_value": canonical_raw_value or text,
                            }
                        )
                continue

            primary_role = canonical_role(default_roles[0]) if len(default_roles) == 1 else ""
            names = split_contributor_value(
                clean_contributor_value(cleaned_segment),
                role=primary_role,
            )
            if not names:
                continue

            if not default_roles and roles_in_text(cleaned_segment):
                continue

            if default_roles:
                for role in default_roles:
                    role = canonical_role(role)
                    for name in names:
                        role_key = (role, normalize_catalog_text(name))
                        if role_key in seen_role_names:
                            continue
                        seen_role_names.add(role_key)
                        contributors.append(
                            {
                                "name": name,
                                "role": role,
                                "raw_value": canonical_raw_value or text,
                            }
                        )
                continue

            for name in names:
                normalized_name = normalize_catalog_text(name)
                if normalized_name in seen_author_names:
                    continue
                seen_author_names.add(normalized_name)
                authors.append(name)

    return {
        "authors": authors,
        "contributors": contributors,
    }


def match_pattern_key(label, pattern_map):
    lowered = clean_display_text(label).lower()
    normalized = normalize_catalog_text(label)
    for key, patterns in pattern_map.items():
        if any(pattern in lowered or normalize_catalog_text(pattern) in normalized for pattern in patterns):
            return key
    return ""

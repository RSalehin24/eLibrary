
BODY_SECTION_PATTERNS = [
    "ভূমিকা",
    "প্রস্তাবনা",
    "লেখকের কথা",
    "অনুবাদকের কথা",
    "প্রকাশকের কথা",
    "সূচিপত্র",
    "অধ্যায়",
    "অধ্যায়",
    "পর্ব",
    "chapter",
    "preface",
    "introduction",
]

SEPARATOR_PARAGRAPH_VALUES = {".", "।", "..", "..."}
BLOCK_TAG_NAMES = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote")
HEADING_TAG_NAMES = {"h1", "h2", "h3", "h4", "h5", "h6"}
MAX_METADATA_TEXT_LENGTH = 320
MAX_METADATA_VALUE_LENGTH = 180
MAX_TITLE_PREFIX_LENGTH = 140
MAX_DEDICATION_BLOCK_LENGTH = 220


def clean_front_matter_label(text):
    return (text or "").strip(" :ঃ-–—").strip()


def is_separator_paragraph(text):
    return clean_front_matter_label(text) in SEPARATOR_PARAGRAPH_VALUES


def text_matches_patterns(text, patterns):
    cleaned = clean_front_matter_label(text).lower()
    normalized = normalize_text(text)
    for pattern in patterns:
        pattern_text = clean_front_matter_label(pattern)
        if not pattern_text:
            continue
        if pattern_text.lower() in cleaned:
            return True
        if normalize_text(pattern_text) in normalized:
            return True
    return False


def looks_like_front_matter_label(label):
    normalized = normalize_text(label)
    return any(normalize_text(pattern) in normalized for pattern in FRONT_MATTER_LABEL_PATTERNS)


def count_sentence_markers(text):
    return len(re.findall(r"[।.!?]", text))


def looks_like_title_prefix(prefix):
    cleaned_prefix = clean_front_matter_label(prefix.strip(" -–—|/"))
    if not cleaned_prefix or len(cleaned_prefix) > MAX_TITLE_PREFIX_LENGTH:
        return False
    if ":" in cleaned_prefix or "ঃ" in cleaned_prefix:
        return False
    if text_matches_patterns(cleaned_prefix, FRONT_MATTER_LABEL_PATTERNS + DEDICATION_PATTERNS + BODY_SECTION_PATTERNS):
        return False
    word_count = len(cleaned_prefix.split())
    return any(separator in prefix for separator in ("-", "–", "—")) or (2 <= word_count <= 10 and len(cleaned_prefix) >= 8)


def search_front_matter_label_value(text, strong_text="", has_break=False):
    cleaned_text = clean_front_matter_label(text)
    cleaned_strong = clean_front_matter_label(strong_text)
    if not cleaned_text or len(cleaned_text) > MAX_METADATA_TEXT_LENGTH:
        return None

    best_candidate = None
    normalized_strong = normalize_text(cleaned_strong)

    for label in sorted(FRONT_MATTER_LABEL_PATTERNS, key=len, reverse=True):
        label_normalized = normalize_text(label)
        pattern = re.compile(
            rf"{re.escape(label)}\s*(?:[:ঃ]\s*|[-–—]\s*|\s+)(?P<value>.+)$",
            re.IGNORECASE,
        )
        for match in pattern.finditer(cleaned_text):
            prefix = cleaned_text[: match.start()]
            cleaned_prefix = clean_front_matter_label(prefix.strip(" -–—|/"))
            value = clean_front_matter_label(match.group("value").strip(" -:ঃ"))
            if not value or len(value) > MAX_METADATA_VALUE_LENGTH:
                continue

            score = 0
            if not cleaned_prefix:
                score += 8
            elif looks_like_title_prefix(prefix):
                score += 6
            elif has_break and len(cleaned_prefix) <= 120:
                score += 5
            elif cleaned_strong and cleaned_prefix and clean_front_matter_label(cleaned_strong) == cleaned_prefix:
                score += 4
            elif cleaned_prefix and len(cleaned_prefix) <= 14:
                score += 1
            else:
                score -= 3

            if normalized_strong and label_normalized in normalized_strong:
                score += 3
            if len(value) <= 80:
                score += 1
            if count_sentence_markers(value) <= 1:
                score += 1
            if score < 5:
                continue

            candidate = {
                "label": cleaned_strong if normalized_strong and label_normalized in normalized_strong else label,
                "value": value,
                "score": score,
                "start": match.start(),
            }
            if best_candidate is None or (candidate["score"], -candidate["start"]) > (
                best_candidate["score"],
                -best_candidate["start"],
            ):
                best_candidate = candidate

    return best_candidate


def extract_front_matter_label_value(paragraph):
    text = clean_front_matter_label(paragraph.get_text(" ", strip=True))
    if not text:
        return "", ""

    strong_text = clean_front_matter_label(" ".join(tag.get_text(" ", strip=True) for tag in paragraph.find_all("strong")))
    candidate = search_front_matter_label_value(text, strong_text=strong_text, has_break=paragraph.find("br") is not None)
    if candidate:
        return candidate["label"], candidate["value"]

    return "", ""


def is_dedication_heading(text, strong_text="", tag_name=""):
    heading_text = clean_front_matter_label(strong_text or text)
    if not heading_text or len(heading_text) > 120:
        return False
    if text_matches_patterns(heading_text, BODY_SECTION_PATTERNS):
        return False
    if not text_matches_patterns(heading_text, DEDICATION_PATTERNS):
        return False
    if search_front_matter_label_value(text, strong_text=strong_text, has_break=False):
        return False
    return tag_name in HEADING_TAG_NAMES or bool(strong_text) or len(heading_text.split()) <= 5


def is_body_section_marker(text, tag_name=""):
    cleaned_text = clean_front_matter_label(text)
    if not cleaned_text:
        return False
    if text_matches_patterns(cleaned_text, BODY_SECTION_PATTERNS) and len(cleaned_text) <= 80:
        return True
    normalized = normalize_text(cleaned_text)
    if tag_name in HEADING_TAG_NAMES and re.search(r"(অধ্যা|পর্ব|chapter)", normalized):
        return True
    return False


def should_continue_dedication_block(text, strong_text="", tag_name=""):
    cleaned_text = clean_front_matter_label(text)
    if not cleaned_text:
        return True
    if is_separator_paragraph(cleaned_text):
        return True
    if is_body_section_marker(cleaned_text, tag_name=tag_name):
        return False
    if tag_name in HEADING_TAG_NAMES and not is_dedication_heading(
        cleaned_text,
        strong_text=strong_text,
        tag_name=tag_name,
    ):
        return False
    if search_front_matter_label_value(cleaned_text, strong_text=strong_text, has_break=False):
        return False
    if is_dedication_heading(cleaned_text, strong_text=strong_text, tag_name=tag_name):
        return False
    if len(cleaned_text) > MAX_DEDICATION_BLOCK_LENGTH:
        return False
    return count_sentence_markers(cleaned_text) <= 3


def extract_content_sections(html_content):
    if not html_content:
        return "", "", html_content

    soup = BeautifulSoup(html_content, "html.parser")
    book_info_parts = []
    dedication_parts = []
    in_dedication = False

    for block in list(soup.find_all(BLOCK_TAG_NAMES)):
        if block.parent is None:
            continue

        text = clean_front_matter_label(block.get_text(" ", strip=True))
        if not text:
            continue

        strong_text = clean_front_matter_label(" ".join(tag.get_text(" ", strip=True) for tag in block.find_all("strong")))

        if in_dedication:
            if should_continue_dedication_block(text, strong_text=strong_text, tag_name=block.name):
                if not is_separator_paragraph(text):
                    dedication_parts.append(str(block))
                block.decompose()
                continue
            in_dedication = False

        metadata_candidate = search_front_matter_label_value(
            text,
            strong_text=strong_text,
            has_break=block.find("br") is not None,
        )
        if metadata_candidate:
            book_info_parts.append(str(block))
            block.decompose()
            continue

        if is_dedication_heading(text, strong_text=strong_text, tag_name=block.name):
            inline_text = clean_front_matter_label(DEDICATION_INLINE_PREFIX_PATTERN.sub("", text, count=1))
            if inline_text and inline_text != clean_front_matter_label(text):
                dedication_parts.append(f"<p>{inline_text}</p>")
            block.decompose()
            in_dedication = True
            continue

        if is_separator_paragraph(text) and (book_info_parts or dedication_parts):
            block.decompose()

    return "\n".join(book_info_parts), "\n".join(dedication_parts), str(soup)

def extract_dedication(html_content):
    """
    Extract labeled book metadata blocks and explicit dedication sections
    from the main content without depending on a fixed order.
    """
    return extract_main_content_segments(html_content)

def sanitize_folder_name(name):
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", "_", name)
    MAX_BYTES = 255
    while len(name.encode("utf-8")) > MAX_BYTES and name:
        name = name[:-1]
    return name.strip("_") or "book"

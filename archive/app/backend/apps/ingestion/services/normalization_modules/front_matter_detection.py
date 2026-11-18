

def resolve_front_section_title(block):
    text = block_text(block)
    if is_front_section_heading(text, tag_name=block.name):
        return text

    strong_heading = block_strong_heading_text(block)
    if strong_heading:
        # A <p> whose entire content is wrapped in <strong> (e.g.
        # <p><strong>চতুর্থ খণ্ডের ভূমিকা</strong></p>) is treated as a
        # structural heading for the purpose of front-section detection.
        # Using tag_name="h2" gives it full heading logic, including the
        # suffix-match path that handles qualified names like
        # "খণ্ডের ভূমিকা" / "সংস্করণের ভূমিকা".
        if is_front_section_heading(strong_heading, tag_name="h2"):
            return strong_heading
        if is_likely_section_title_text(strong_heading):
            return strong_heading

    return ""


def looks_like_title_prefix(prefix):
    cleaned_prefix = clean_display_text(prefix.strip(" -–—|/"))
    if not cleaned_prefix or len(cleaned_prefix) > MAX_TITLE_PREFIX_LENGTH:
        return False
    if re.search(r"[,;।.!?]", cleaned_prefix):
        return False
    if has_non_name_phrase_marker(cleaned_prefix):
        return False
    if ":" in cleaned_prefix or "ঃ" in cleaned_prefix:
        return False
    if text_matches_patterns(cleaned_prefix, ALL_METADATA_LABELS + DEDICATION_PATTERNS + BODY_SECTION_PATTERNS):
        return False
    word_count = len(cleaned_prefix.split())
    return any(separator in prefix for separator in ("-", "–", "—")) or (2 <= word_count <= 10 and len(cleaned_prefix) >= 8)


def is_plausible_metadata_value(entry, value):
    cleaned_value = clean_display_text(value)
    if not cleaned_value:
        return False

    if entry["role"]:
        candidates = split_contributor_value(
            clean_contributor_value(cleaned_value),
            role=entry["role"],
        )
        if not candidates:
            return False
        if len(cleaned_value.split()) > 8 and all(len(candidate.split()) == 1 for candidate in candidates):
            return False
        return True

    sentence_markers = count_sentence_markers(cleaned_value)
    if sentence_markers > 1:
        return False
    if sentence_markers == 1 and len(cleaned_value.split()) > 6:
        return False
    if text_matches_patterns(cleaned_value, BODY_SECTION_PATTERNS) and len(cleaned_value) <= 80:
        return False
    return True


def search_front_matter_label_value(text, strong_text="", has_break=False):
    cleaned_text = clean_display_text(text)
    cleaned_strong = clean_display_text(strong_text)
    if not cleaned_text or len(cleaned_text) > MAX_METADATA_TEXT_LENGTH:
        return None

    best_candidate = None
    normalized_strong = normalize_catalog_text(cleaned_strong)

    for entry in METADATA_LABEL_ALIASES:
        alias = entry["alias"]
        alias_normalized = normalize_catalog_text(alias)
        pattern = re.compile(
            rf"{re.escape(alias)}\s*(?P<separator>[:ঃ]\s*|[-–—]\s*|\s+)(?P<value>.+)$",
            re.IGNORECASE,
        )
        for match in pattern.finditer(cleaned_text):
            start_index = match.start()
            end_index = start_index + len(alias)
            if start_index > 0 and re.match(r"[A-Za-z0-9_\u0980-\u09FF]", cleaned_text[start_index - 1]):
                continue
            if end_index < len(cleaned_text) and re.match(r"[A-Za-z0-9_\u0980-\u09FF]", cleaned_text[end_index]):
                continue

            prefix = cleaned_text[: match.start()]
            cleaned_prefix = clean_display_text(prefix.strip(" -–—|/"))
            separator = match.group("separator") or ""
            if (
                alias_normalized in EXPLICIT_SEPARATOR_ONLY_LABELS
                and separator.isspace()
            ):
                continue
            value = clean_display_text(match.group("value").strip(" -:ঃ–—"))
            if (
                cleaned_prefix
                and separator.isspace()
                and not cleaned_strong
                and not has_break
            ):
                continue
            if not value or len(value) > MAX_METADATA_VALUE_LENGTH or not is_plausible_metadata_value(entry, value):
                continue

            score = 0
            if not cleaned_prefix:
                score += 8
            elif looks_like_title_prefix(prefix):
                score += 6
            elif has_break and len(cleaned_prefix) <= 120:
                score += 5
            elif cleaned_strong and cleaned_prefix and clean_display_text(cleaned_strong) == cleaned_prefix:
                score += 4
            elif cleaned_prefix and len(cleaned_prefix) <= 14:
                score += 1
            else:
                score -= 3

            if normalized_strong and alias_normalized in normalized_strong:
                score += 3
            if len(value) <= 80:
                score += 1
            if count_sentence_markers(value) <= 1:
                score += 1
            if score < 5:
                continue

            label = cleaned_strong if normalized_strong and alias_normalized in normalized_strong else alias
            cleaned_value = (
                clean_contributor_value(value)
                if entry["role"]
                else value
            )
            candidate = {
                "label": clean_display_text(label),
                "value": cleaned_value,
                "role": entry["role"],
                "key": entry["key"],
                "score": score,
                "start": match.start(),
            }
            if best_candidate is None or (candidate["score"], -candidate["start"]) > (
                best_candidate["score"],
                -best_candidate["start"],
            ):
                best_candidate = candidate

    return best_candidate


def parse_front_matter_line(text, strong_text="", has_break=False):
    candidate = search_front_matter_label_value(text, strong_text=strong_text, has_break=has_break)
    if not candidate:
        return "", ""
    return candidate["label"], candidate["value"]


def is_dedication_heading(text, strong_text="", tag_name=""):
    heading_text = clean_display_text(strong_text or text)
    if not heading_text or len(heading_text) > 120:
        return False
    if text_matches_patterns(heading_text, BODY_SECTION_PATTERNS):
        return False
    if not heading_matches_patterns(heading_text, DEDICATION_PATTERNS):
        return False
    if search_front_matter_label_value(text, strong_text=strong_text, has_break=False):
        return False
    return tag_name in HEADING_TAG_NAMES or bool(strong_text) or len(heading_text.split()) <= 5


def is_body_section_marker(text, tag_name=""):
    cleaned_text = clean_display_text(text)
    if not cleaned_text:
        return False
    if heading_matches_patterns(cleaned_text, BODY_SECTION_PATTERNS) and len(cleaned_text) <= 80:
        return True
    normalized = normalize_catalog_text(cleaned_text)
    if tag_name in HEADING_TAG_NAMES and re.search(r"(অধ্যা|পর্ব|chapter)", normalized):
        return True
    return False


def should_continue_dedication_block(text, strong_text="", tag_name=""):
    cleaned_text = clean_display_text(text)
    if not cleaned_text:
        return True
    if is_separator_paragraph(cleaned_text):
        return True
    if is_body_section_marker(cleaned_text, tag_name=tag_name):
        return False
    # Numeric poem/chapter ordinal marker (e.g. "১.", "২.", "1.") — signals the
    # start of body content and must stop dedication extraction immediately.
    if re.match(r'^[০-৯0-9]+\.?\s*$', cleaned_text):
        return False
    if is_non_dedication_strong_heading(cleaned_text, strong_text=strong_text, tag_name=tag_name):
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
    if looks_like_letter_excerpt_marker(cleaned_text):
        return False
    if len(cleaned_text) > MAX_DEDICATION_BLOCK_LENGTH:
        return False
    return count_sentence_markers(cleaned_text) <= 8


def looks_like_letter_excerpt_marker(text):
    cleaned_text = clean_display_text(text)
    if not cleaned_text:
        return False
    normalized = normalize_catalog_text(cleaned_text)

    if DATE_LINE_PATTERN.fullmatch(cleaned_text):
        return True
    if LETTER_SALUTATION_PATTERN.match(cleaned_text):
        return True
    for pattern in LETTER_EXCERPT_PATTERNS:
        if normalize_catalog_text(pattern) in normalized:
            return True
    return False


def is_front_section_heading(text, tag_name=""):
    cleaned_text = clean_display_text(text)
    if not cleaned_text or len(cleaned_text) > 140:
        return False
    if not heading_matches_patterns(cleaned_text, FRONT_SECTION_HEADING_PATTERNS):
        # Also match when a known front-section keyword appears as a *suffix*
        # e.g. "চতুর্থ খণ্ডের ভূমিকা" — ভূমিকা is at the end, preceded by a
        # qualifier phrase.  Restrict this to structural heading elements
        # (h2/h3/h4…) only — paragraph body text that happens to end in ভূমিকা
        # (e.g. "মূল বইয়ের ভূমিকা" as running prose) must NOT be classified as
        # a front-section heading.
        if tag_name not in HEADING_TAG_NAMES:
            return False
        normalized = normalize_catalog_text(cleaned_text)
        suffix_matched = any(
            normalized.endswith(f" {normalize_catalog_text(p)}")
            for p in FRONT_SECTION_HEADING_PATTERNS
            if p and normalize_catalog_text(p)
        )
        if not suffix_matched:
            return False
        # Reject if the prefix (everything before the keyword) contains
        # content-chapter markers that suggest this is a chapter heading.
        prefix_text = clean_display_text(
            re.sub(
                r"\s+" + re.escape(cleaned_text.rsplit(None, 1)[-1]) + r"\s*$",
                "",
                cleaned_text,
            )
        )
        if prefix_text and re.search(r"[।.!?]", prefix_text):
            return False
    normalized = normalize_catalog_text(cleaned_text)
    is_supplementary_chapter = heading_matches_patterns(
        cleaned_text,
        SUPPLEMENTARY_CHAPTER_HEADING_PATTERNS,
    )
    if re.search(r"(অধ্যা|পর্ব|chapter)", normalized) and not is_supplementary_chapter:
        return False
    return tag_name in HEADING_TAG_NAMES or len(cleaned_text.split()) <= 8

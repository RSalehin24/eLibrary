from .front_matter_text_rules import (
    BODY_SECTION_PATTERNS,
    clean_contributor_value,
    clean_display_text,
    count_sentence_markers,
    split_contributor_value,
    text_matches_patterns,
)


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


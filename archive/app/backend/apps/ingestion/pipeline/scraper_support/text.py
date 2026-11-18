import re
import unicodedata


def normalize_text(text):
    """
    Normalize text for comparison by removing all symbols and punctuation.
    Only keeps letters, numbers, combining marks, and spaces for matching.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text).lower()

    normalized = []
    for char in text:
        if char.isspace():
            normalized.append(" ")
            continue
        category = unicodedata.category(char)
        if category.startswith(("L", "N", "M")):
            normalized.append(char)

    text = "".join(normalized)
    return re.sub(r"\s+", " ", text).strip()


def normalize_bengali_numbers(text):
    """
    Convert Bengali word numbers to digit format and vice versa for comparison.
    Returns a list of possible normalized versions.
    """
    if not text:
        return [""]

    word_to_digit = {
        "প্রথম": "1ম",
        "দ্বিতীয়": "2য়",
        "তৃতীয়": "3য়",
        "চতুর্থ": "4র্থ",
        "পঞ্চম": "5ম",
        "ষষ্ঠ": "6ষ্ঠ",
        "সপ্তম": "7ম",
        "অষ্টম": "8ম",
        "নবম": "9ম",
        "দশম": "10ম",
    }
    bengali_to_english = {
        "০": "0",
        "১": "1",
        "২": "2",
        "৩": "3",
        "৪": "4",
        "৫": "5",
        "৬": "6",
        "৭": "7",
        "৮": "8",
        "৯": "9",
    }

    normalized = normalize_text(text)
    versions = [normalized]

    english_version = normalized
    for bengali_digit, english_digit in bengali_to_english.items():
        english_version = english_version.replace(bengali_digit, english_digit)
    if english_version != normalized:
        versions.append(english_version)

    for word, digit in word_to_digit.items():
        word_norm = normalize_text(word)
        digit_norm = normalize_text(digit)
        if word_norm in normalized:
            versions.append(normalized.replace(word_norm, digit_norm))

    return versions


def extract_core_title(text):
    """Extract the core title by removing trailing author-like metadata."""
    if not text:
        return ""

    normalized = normalize_text(text)
    author_indicators = [
        "লখক",
        "অনবদক",
        "সমপদক",
        "রপনতর",
        "মল",
        "অনবদ",
        "রচন",
        "সকলন",
    ]
    parts = normalized.split()
    core_parts = []
    for index, part in enumerate(parts):
        is_author_indicator = any(indicator in part for indicator in author_indicators)
        if is_author_indicator and index > 0:
            break
        core_parts.append(part)

    return " ".join(core_parts)


def texts_are_similar(text1, text2, debug=False):
    """Check if two texts are similar enough to be considered duplicates."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    if debug:
        print("  Comparing:")
        print(f"    Original 1: '{text1}'")
        print(f"    Original 2: '{text2}'")
        print(f"    Normalized 1: '{norm1}'")
        print(f"    Normalized 2: '{norm2}'")

    if norm1 == norm2:
        if debug:
            print("    Result: EXACT MATCH")
        return True

    if len(norm1) > 10 and len(norm2) > 10 and (norm1 in norm2 or norm2 in norm1):
        if debug:
            print("    Result: SUBSTRING MATCH")
        return True

    core1 = extract_core_title(text1)
    core2 = extract_core_title(text2)
    if core1 and core2 and len(core1) > 5 and len(core2) > 5:
        if core1 == core2:
            if debug:
                print(f"    Result: CORE TITLE MATCH ('{core1}' == '{core2}')")
            return True
        if core1 in core2 or core2 in core1:
            if debug:
                print("    Result: CORE TITLE SUBSTRING MATCH")
            return True

    versions1 = normalize_bengali_numbers(text1)
    versions2 = normalize_bengali_numbers(text2)
    for version_one in versions1:
        for version_two in versions2:
            if version_one == version_two:
                if debug:
                    print("    Result: NUMBER-NORMALIZED MATCH")
                return True
            if (
                len(version_one) > 10
                and len(version_two) > 10
                and (version_one in version_two or version_two in version_one)
            ):
                if debug:
                    print("    Result: NUMBER-NORMALIZED SUBSTRING MATCH")
                return True

    common_prefixes = ["লখক", "অনবদক", "সমপদক", "মল"]
    for prefix in common_prefixes:
        clean1 = norm1.replace(prefix, "").strip()
        clean2 = norm2.replace(prefix, "").strip()
        if clean1 and clean2 and clean1 == clean2:
            if debug:
                print(f"    Result: PREFIX-STRIPPED MATCH ({prefix})")
            return True

    if debug:
        print("    Result: NO MATCH")
    return False

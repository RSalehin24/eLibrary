

def split_leading_front_sections(main_content_html, *, has_explicit_body=False):
    """Extract leading front-matter sections from main content.

    ``has_explicit_body`` should be set True when the book already has body
    chapters from a source-side TOC (lessons/topics). In that case the
    landing main content is by definition pure front-matter, so:
      * lone numeric paragraphs ("১.", "২.", "৩." …) cannot be chapter
        markers — they are enumeration inside the foreword and must be
        absorbed into the current section rather than terminate extraction.
      * unrecognised heading tags / strong-text titles inside the landing
        content should flush the current section and start a NEW front
        section (so each separator-divided block becomes its own page),
        not terminate extraction.
    """
    if not main_content_html:
        return [], main_content_html

    soup = BeautifulSoup(main_content_html, "html.parser")
    remove_source_generated_toc_containers(soup)
    sections = []
    current_section = None
    extraction_started = False

    def _flush_unnamed_section():
        nonlocal current_section
        if not current_section:
            return
        html_parts = current_section["html_parts"]
        title = current_section["title"]
        if plain_text_from_html("\n".join(html_parts)):
            sections.append({"title": title, "html": "\n".join(html_parts)})
        current_section = None

    for block in list(soup.find_all(BLOCK_TAG_NAMES)):
        if block.parent is None:
            continue

        text = block_text(block)
        if not text:
            continue

        strong_text = block_strong_text(block)
        has_break = block_has_break(block)

        section_title = resolve_front_section_title(block)
        if section_title:
            is_recognized = (
                is_front_section_heading(section_title, tag_name=block.name)
                or text_matches_patterns(section_title, ["সংস্করণ", "edition"])
                or has_break  # multiline compound headings (title + author/translator via <br/>)
            )
            if not extraction_started and not is_recognized and not has_explicit_body:
                continue
            if extraction_started and not is_recognized and not has_explicit_body:
                # Before stopping, remove inline TOC headings (e.g. সূচীপত্র) if present
                if text_matches_patterns(text, INLINE_TOC_HEADING_PATTERNS):
                    remove_inline_toc_heading_and_lists(block)
                break
            extraction_started = True
            if current_section:
                _flush_unnamed_section()
            current_section = {"title": section_title, "html_parts": []}
            block.decompose()
            continue

        if not extraction_started:
            if has_explicit_body:
                # Source has its own body TOC, so landing content is pure
                # front-matter. Seed an implicit (untitled) section so the
                # first paragraphs aren't dropped while we wait for a
                # recognised heading.
                extraction_started = True
                current_section = {"title": "", "html_parts": []}
            else:
                continue

        if is_separator_paragraph(text):
            if has_explicit_body:
                _flush_unnamed_section()
            block.decompose()
            continue
        if is_dot_bracketed_section_boundary(text):
            _flush_unnamed_section()
            block.decompose()
            continue
        if text_matches_patterns(text, INLINE_TOC_HEADING_PATTERNS):
            remove_inline_toc_heading_and_lists(block)
            break

        if is_dedication_heading(text, strong_text=strong_text, tag_name=block.name):
            break
        if search_front_matter_label_value(text, strong_text=strong_text, has_break=has_break):
            break
        if is_body_section_marker(text, tag_name=block.name) and not has_explicit_body:
            break
        if numbered_section_marker_value(text) is not None and not has_explicit_body:
            break
        if (
            block.name in HEADING_TAG_NAMES
            and not is_front_section_heading(text, tag_name=block.name)
            and not has_explicit_body
        ):
            break

        if current_section is None:
            if has_explicit_body:
                current_section = {"title": "", "html_parts": []}
            else:
                break

        current_section["html_parts"].append(str(block))
        block.decompose()

    _flush_unnamed_section()

    if sections:
        strip_leading_probable_toc_lists(soup)

    return sections, str(soup)


MIN_DUPLICATE_FRAGMENT_SIGNATURE_LENGTH = 8
SHORT_RESIDUAL_MAIN_CONTENT_LENGTH = 180
BANGLA_TO_ASCII_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
NUMERIC_ONLY_SECTION_MARKER_PATTERN = re.compile(
    r"^(?P<digits>[০-৯0-9]{1,4})(?:\s*[.)।])?$",
)
TOC_SECTION_TITLE_PATTERNS = tuple([*INLINE_TOC_HEADING_PATTERNS, "সূচী"])


def normalized_fragment_signature(text):
    cleaned = clean_display_text(text or "")
    if not cleaned:
        return ""
    return normalize_catalog_text(cleaned)


def numbered_section_marker_value(text):
    cleaned_text = clean_display_text(text or "")
    if not cleaned_text or len(cleaned_text) > 8:
        return None

    match = NUMERIC_ONLY_SECTION_MARKER_PATTERN.fullmatch(cleaned_text)
    if not match:
        return None

    ascii_digits = match.group("digits").translate(BANGLA_TO_ASCII_DIGITS)
    if not ascii_digits.isdigit():
        return None

    return int(ascii_digits)


def numbered_section_title(number):
    return str(int(number)).translate(ASCII_TO_BANGLA_DIGITS)


def is_probable_source_navigation_section(title, html):
    normalized_title = normalize_catalog_text(title or "")
    if not normalized_title:
        return False

    if not any(
        normalized_title == normalize_catalog_text(pattern)
        or normalized_title.startswith(f"{normalize_catalog_text(pattern)} ")
        for pattern in TOC_SECTION_TITLE_PATTERNS
    ):
        return False

    soup = BeautifulSoup(html or "", "html.parser")
    anchors = [
        anchor
        for anchor in soup.find_all("a", href=True)
        if clean_display_text(anchor.get_text(" ", strip=True))
    ]
    if len(anchors) < 3:
        return False

    external_book_links = 0
    for anchor in anchors:
        href = clean_display_text(anchor.get("href", ""))
        if not href:
            continue
        if href.startswith("#"):
            continue
        if "/books/" in href:
            external_book_links += 1

    return external_book_links >= max(3, int(len(anchors) * 0.75))


def iter_fragment_blocks(html):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    return [
        block
        for block in soup.find_all(BLOCK_TAG_NAMES)
        if block.parent is not None and block_text(block)
    ]


def collect_fragment_signatures(*html_fragments):
    signatures = set()
    for fragment in html_fragments:
        for block in iter_fragment_blocks(fragment):
            signature = normalized_fragment_signature(block_text(block))
            if signature:
                signatures.add(signature)
    return signatures


def dedupe_html_fragment_blocks(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    seen = set()

    for block in list(soup.find_all(BLOCK_TAG_NAMES)):
        if block.parent is None:
            continue

        text = block_text(block)
        signature = normalized_fragment_signature(text)
        if not signature:
            continue
        if len(signature) < MIN_DUPLICATE_FRAGMENT_SIGNATURE_LENGTH:
            seen.add(signature)
            continue
        if signature in seen:
            block.decompose()
            continue
        seen.add(signature)

    cleaned_html = str(soup).strip()
    return cleaned_html if plain_text_from_html(cleaned_html) else ""


def merge_front_matter_html_parts(*html_fragments):
    merged_blocks = []
    seen = set()

    for fragment in html_fragments:
        if not fragment:
            continue

        blocks = iter_fragment_blocks(fragment)
        if not blocks:
            cleaned_text = clean_display_text(plain_text_from_html(fragment))
            signature = normalized_fragment_signature(cleaned_text)
            if cleaned_text and signature and signature not in seen:
                seen.add(signature)
                merged_blocks.append(f"<p>{escape(cleaned_text)}</p>")
            continue

        for block in blocks:
            signature = normalized_fragment_signature(block_text(block))
            if signature and signature in seen:
                continue
            if signature:
                seen.add(signature)
            merged_blocks.append(str(block))

    merged_html = "\n".join(merged_blocks).strip()
    return merged_html if plain_text_from_html(merged_html) else ""


def dedupe_structured_sections(sections, *, reference_fragments=None):
    reference_signatures = collect_fragment_signatures(*(reference_fragments or []))
    deduped = []
    seen = set()

    for section in sections or []:
        title = clean_display_text((section or {}).get("title") or "")
        html = str((section or {}).get("html") or "").strip()
        if reference_signatures and html:
            soup = BeautifulSoup(html, "html.parser")
            for block in list(soup.find_all(BLOCK_TAG_NAMES)):
                if block.parent is None:
                    continue
                signature = normalized_fragment_signature(block_text(block))
                if (
                    signature
                    and len(signature) >= MIN_DUPLICATE_FRAGMENT_SIGNATURE_LENGTH
                    and signature in reference_signatures
                ):
                    block.decompose()
            html = str(soup).strip()

        plain_text = clean_display_text(plain_text_from_html(html))
        if not plain_text:
            continue
        if is_probable_source_navigation_section(title, html):
            continue

        signature = (
            normalize_catalog_text(title),
            normalize_catalog_text(plain_text),
        )
        if signature in seen:
            continue

        merged = False
        for existing_section in deduped:
            existing_title = normalize_catalog_text(existing_section["title"])
            existing_text = clean_display_text(plain_text_from_html(existing_section["html"]))
            existing_signature = normalize_catalog_text(existing_text)
            if existing_title != signature[0]:
                continue

            longer_signature, shorter_signature = sorted(
                [signature[1], existing_signature],
                key=len,
                reverse=True,
            )
            length_delta = abs(len(signature[1]) - len(existing_signature))
            if (
                shorter_signature
                and shorter_signature in longer_signature
                and length_delta <= max(80, int(len(longer_signature) * 0.05))
            ):
                if len(signature[1]) < len(existing_signature):
                    existing_section["html"] = html
                merged = True
                break

        if merged:
            continue

        seen.add(signature)
        deduped.append({"title": title, "html": html})

    return deduped


def prune_duplicate_main_content(
    main_content_html,
    *,
    reference_fragments=None,
    content_items=None,
):
    if not main_content_html:
        return ""

    reference_signatures = collect_fragment_signatures(*(reference_fragments or []))
    if not reference_signatures:
        return main_content_html

    soup = BeautifulSoup(main_content_html, "html.parser")
    for block in list(soup.find_all(BLOCK_TAG_NAMES)):
        if block.parent is None:
            continue

        signature = normalized_fragment_signature(block_text(block))
        if (
            signature
            and len(signature) >= MIN_DUPLICATE_FRAGMENT_SIGNATURE_LENGTH
            and signature in reference_signatures
        ):
            block.decompose()

    cleaned_html = str(soup).strip()
    remaining_text = clean_display_text(plain_text_from_html(cleaned_html))
    if not remaining_text:
        return ""

    remaining_blocks = [
        clean_display_text(block_text(block))
        for block in soup.find_all(BLOCK_TAG_NAMES)
        if block.parent is not None and block_text(block)
    ]
    if (
        content_items
        and remaining_blocks
        and len(remaining_text) <= SHORT_RESIDUAL_MAIN_CONTENT_LENGTH
        and all(
            normalized_fragment_signature(text) in reference_signatures or len(text) <= 24
            for text in remaining_blocks
        )
    ):
        return ""

    return cleaned_html


def strip_leading_dedication_label(text):
    cleaned_text = clean_display_text(text)
    if not cleaned_text:
        return ""
    stripped = DEDICATION_INLINE_PREFIX_PATTERN.sub("", cleaned_text, count=1)
    return clean_display_text(stripped)


def lines_to_paragraphs_html(lines):
    cleaned_lines = [clean_display_text(line) for line in lines if clean_display_text(line)]
    if not cleaned_lines:
        return ""
    return "".join(f"<p>{escape(line)}</p>" for line in cleaned_lines)


def split_block_on_inline_dedication(block):
    if block.name not in {"p", "li", "blockquote"}:
        return None

    raw_text = block.get_text("\n", strip=True)
    if not raw_text:
        return None

    lines = [clean_display_text(line) for line in raw_text.splitlines() if clean_display_text(line)]
    if not lines:
        return None

    dedication_index = -1
    for index, line in enumerate(lines):
        if DEDICATION_INLINE_PREFIX_PATTERN.match(line):
            dedication_index = index
            break

    if dedication_index < 0:
        return None

    before_lines = lines[:dedication_index]
    dedication_lines = []

    first_dedication_line = strip_leading_dedication_label(lines[dedication_index])
    if first_dedication_line:
        dedication_lines.append(first_dedication_line)

    dedication_lines.extend(lines[dedication_index + 1 :])

    return {
        "before_html": lines_to_paragraphs_html(before_lines),
        "dedication_html": lines_to_paragraphs_html(dedication_lines),
    }


def extract_main_content_segments(main_content_html):
    if not main_content_html:
        return "", "", main_content_html

    soup = BeautifulSoup(main_content_html, "html.parser")
    remove_source_generated_toc_containers(soup)
    book_info_parts = []
    dedication_parts = []
    in_dedication = False

    for block in list(soup.find_all(BLOCK_TAG_NAMES)):
        if block.parent is None:
            continue

        text = block_text(block)
        if not text:
            continue

        strong_text = block_strong_text(block)
        has_break = block_has_break(block)

        if in_dedication:
            if is_separator_paragraph(text) or is_dot_bracketed_section_boundary(text):
                in_dedication = False
                block.decompose()
                continue
            if should_continue_dedication_block(text, strong_text=strong_text, tag_name=block.name):
                dedication_parts.append(str(block))
                block.decompose()
                continue
            in_dedication = False

        inline_dedication_split = split_block_on_inline_dedication(block)
        if inline_dedication_split is not None:
            before_html = inline_dedication_split["before_html"]
            dedication_html = inline_dedication_split["dedication_html"]

            if before_html:
                replacement_soup = BeautifulSoup(before_html, "html.parser")
                block.clear()
                for child in list(replacement_soup.contents):
                    block.append(child)
            else:
                block.decompose()

            if dedication_html:
                dedication_parts.append(dedication_html)

            in_dedication = True
            continue

        metadata_candidate = search_front_matter_label_value(text, strong_text=strong_text, has_break=has_break)
        if metadata_candidate:
            book_info_parts.append(str(block))
            block.decompose()
            continue

        if "/" in text:
            slash_parts = [p.strip() for p in text.split("/")]
            if len(slash_parts) >= 3 and any(
                search_front_matter_label_value(p, strong_text=p, has_break=False)
                for p in slash_parts
            ):
                book_info_parts.append(str(block))
                block.decompose()
                continue

        # Compound paragraph: multiple sentences separated by "।" where some are
        # key-value metadata (e.g. "প্রথম প্রকাশ – জানুয়ারি ১৯৯৮") and others
        # are prose or story-lists.  Extract ONLY the metadata sub-sentences as
        # individual elements in book_info; leave the rest in main content.
        if "।" in text:
            danda_parts = [p.strip() for p in text.split("।") if p.strip()]
            if len(danda_parts) >= 2:
                meta_subs = [
                    p for p in danda_parts
                    if search_front_matter_label_value(p, strong_text=p, has_break=False)
                ]
                if meta_subs:
                    non_meta_subs = [
                        p for p in danda_parts
                        if not search_front_matter_label_value(p, strong_text=p, has_break=False)
                    ]
                    for part in meta_subs:
                        book_info_parts.append(f"<{block.name}>{part}</{block.name}>")
                    if non_meta_subs:
                        block.clear()
                        block.append("। ".join(non_meta_subs))
                    else:
                        block.decompose()
                    continue

        if is_dedication_heading(text, strong_text=strong_text, tag_name=block.name):
            block.decompose()
            in_dedication = True
            continue

        # NOTE: we intentionally do NOT decompose separator paragraphs that
        # are not adjacent to a dedication/book_info block. Downstream
        # front-section splitting (``split_leading_front_sections``) relies
        # on these ``<p>.</p>``-style separators to flush each landing
        # front-matter chunk into its own section (e.g. the writer's word
        # block that follows the disclaimer/বিধিসম্মত সতর্কীকরণ section).

    return "\n".join(book_info_parts), clean_extracted_dedication_html("\n".join(dedication_parts)), str(soup)


ASCII_TO_BANGLA_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
CHAPTER_SECTION_KEYWORD_PATTERN = re.compile(
    r"(?:(?:^|\s)(?:অধ্যা(?:য়|য|য়)?|পর্ব|খণ্ড|পরিচ্ছেদ|অংশ)(?:\s|[০-৯0-9]|$)|\b(?:chapter|part|section)\b)",
    re.IGNORECASE,
)
NUMERIC_SECTION_PREFIX_PATTERN = re.compile(
    r"^(?:[০-৯0-9]+(?:\s*[\.\):]|(?:\s+(?:অধ্যা|অধ্যায়|পর্ব|খণ্ড|chapter|part|section)\b)))",
    re.IGNORECASE,
)
ORDINAL_SECTION_PREFIX_PATTERN = re.compile(
    r"^(?:প্রথম|দ্বিতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম"
    r"|এক|দুই|তিন|চার|পাঁচ|ছয়|সাত|আট|নয়|দশ"
    r"|এগারো|বারো|তেরো|চোদ্দো|চোদ্দ|পনেরো|ষোলো|সতেরো|আঠারো|উনিশ|বিশ"
    r")\b",
    re.IGNORECASE,
)


def normalize_structured_section_title(title):
    cleaned = clean_display_text(title or "")
    if not cleaned:
        return ""
    return cleaned.translate(ASCII_TO_BANGLA_DIGITS)


def block_heading_candidate_text(block):
    block_label = heading_plain_text(block_text(block))
    if not block_label or len(block_label) > 180:
        return ""

    strong_heading = block_strong_heading_text(block)
    candidate = heading_plain_text(strong_heading or block_label)
    if not candidate:
        return ""
    loose_heading = False
    if block.name not in HEADING_TAG_NAMES and not strong_heading:
        normalized_candidate = normalize_catalog_text(candidate)
        child_tags = {
            child.name
            for child in block.find_all(recursive=False)
            if isinstance(child, Tag) and child.name
        }
        loose_heading = (
            len(candidate) <= 120
            and len(candidate.split()) <= 12
            and count_sentence_markers(candidate) == 0
            and not text_matches_patterns(candidate, INLINE_TOC_HEADING_PATTERNS)
            and not search_front_matter_label_value(
                block_label,
                strong_text=block_strong_text(block),
                has_break=block_has_break(block),
            )
            and not is_dedication_heading(
                block_label,
                strong_text=block_strong_text(block),
                tag_name=block.name,
            )
            and not is_front_section_heading(candidate, tag_name=block.name)
            and (
                bool(CHAPTER_SECTION_KEYWORD_PATTERN.search(normalized_candidate))
                or bool(NUMERIC_SECTION_PREFIX_PATTERN.match(candidate))
                or bool(child_tags & {"strong", "b", "em", "u", "span"})
            )
        )
    if block.name not in HEADING_TAG_NAMES and not strong_heading and not loose_heading:
        return ""
    if count_sentence_markers(candidate) > 1 or len(candidate.split()) > 18:
        return ""
    if text_matches_patterns(candidate, INLINE_TOC_HEADING_PATTERNS):
        return ""
    if search_front_matter_label_value(
        block_label,
        strong_text=strong_heading or block_strong_text(block),
        has_break=block_has_break(block),
    ):
        return ""
    if is_dedication_heading(
        block_label,
        strong_text=strong_heading or block_strong_text(block),
        tag_name=block.name,
    ):
        return ""
    if is_front_section_heading(candidate, tag_name=block.name):
        return ""
    return normalize_structured_section_title(candidate)


def structured_body_heading_score(title, *, tag_name=""):
    normalized = normalize_catalog_text(title)
    if not normalized:
        return 0

    score = 0
    if CHAPTER_SECTION_KEYWORD_PATTERN.search(normalized):
        score += 3
    if NUMERIC_SECTION_PREFIX_PATTERN.match(title):
        score += 3
    if ORDINAL_SECTION_PREFIX_PATTERN.match(normalized):
        score += 2
    if tag_name in HEADING_TAG_NAMES:
        score += 1
    if len(title.split()) <= 8:
        score += 1
    return score


def build_flat_toc_from_content_items(content_items):
    toc = []
    for item in content_items:
        path = item.get("path") or [item.get("title", "")]
        toc.append(
            {
                "title": item.get("title", ""),
                "type": item.get("type", "lesson"),
                "has_content": bool(plain_text_from_html(item.get("content", ""))),
                "path": list(path),
            }
        )
    return toc


def infer_numeric_structured_content_from_main_content(main_content_html):
    if not main_content_html:
        return [], [], main_content_html

    soup = BeautifulSoup(main_content_html, "html.parser")
    blocks = [
        block
        for block in soup.find_all(BLOCK_TAG_NAMES)
        if block.parent is not None and block_text(block)
    ]
    if len(blocks) < 4:
        return [], [], main_content_html

    markers = []
    for index, block in enumerate(blocks):
        if block.name not in {"p", "li", "blockquote"}:
            continue
        number = numbered_section_marker_value(block_text(block))
        if number is None:
            continue
        markers.append({"index": index, "number": number})

    if len(markers) < 2:
        return [], [], main_content_html

    numbers = [marker["number"] for marker in markers]
    if numbers[0] not in {1, 2}:
        return [], [], main_content_html

    sequential_steps = sum(
        1
        for number, next_number in zip(numbers, numbers[1:])
        if next_number == number + 1
    )
    if sequential_steps < max(1, len(markers) - 2):
        return [], [], main_content_html

    section_specs = []
    consumed_indices = set()
    first_marker = markers[0]
    leading_html = "\n".join(str(blocks[index]) for index in range(first_marker["index"])).strip()
    leading_text = clean_display_text(plain_text_from_html(leading_html))

    if first_marker["number"] == 2:
        if len(leading_text) < 20:
            return [], [], main_content_html
        section_specs.append(
            {
                "title": numbered_section_title(1),
                "html": leading_html,
            }
        )
        consumed_indices.update(range(first_marker["index"]))

    for marker_index, marker in enumerate(markers):
        start = marker["index"] + 1
        end = markers[marker_index + 1]["index"] if marker_index + 1 < len(markers) else len(blocks)
        section_html = "\n".join(str(blocks[index]) for index in range(start, end)).strip()
        section_text = clean_display_text(plain_text_from_html(section_html))
        if len(section_text) < 20:
            return [], [], main_content_html

        section_specs.append(
            {
                "title": numbered_section_title(marker["number"]),
                "html": section_html,
            }
        )
        consumed_indices.add(marker["index"])
        consumed_indices.update(range(start, end))

    if len(section_specs) < 2:
        return [], [], main_content_html

    content_items = [
        {
            "title": section["title"],
            "content": section["html"],
            "type": "lesson",
            "parent": None,
            "path": [section["title"]],
        }
        for section in section_specs
    ]

    residual_html = "\n".join(
        str(blocks[index])
        for index in range(len(blocks))
        if index not in consumed_indices
    ).strip()

    return build_flat_toc_from_content_items(content_items), content_items, residual_html


def prune_toc_entries_without_content(toc_entries, content_items, parent_path=()):
    non_empty_paths = {
        tuple(item.get("path") or [])
        for item in content_items
        if plain_text_from_html(item.get("content", ""))
        or (item.get("has_content") is None and "has_content" in item and "source_url" in item)
    }

    def prune(entries, base_path=()):
        pruned = []
        for entry in entries or []:
            path = tuple(entry.get("path") or (tuple(base_path) + (entry.get("title", ""),)))
            children = prune(entry.get("children", []), path)
            has_content = path in non_empty_paths
            if not has_content and not children:
                continue
            normalized_entry = {
                **entry,
                "path": list(path),
                "has_content": has_content,
            }
            if children:
                normalized_entry["children"] = children
            else:
                normalized_entry.pop("children", None)
            pruned.append(normalized_entry)
        return pruned

    return prune(toc_entries, parent_path)


def infer_structured_content_from_main_content(main_content_html, book_title=""):
    if not main_content_html:
        return [], [], main_content_html

    soup = BeautifulSoup(main_content_html, "html.parser")
    blocks = [block for block in list(soup.find_all(BLOCK_TAG_NAMES)) if block.parent is not None]
    candidates = []
    normalized_book_title = normalize_catalog_text(book_title)

    for index, block in enumerate(blocks):
        heading = block_heading_candidate_text(block)
        if not heading:
            continue
        if index == 0 and normalized_book_title and normalize_catalog_text(heading) == normalized_book_title:
            continue
        score = structured_body_heading_score(heading, tag_name=block.name)
        candidates.append(
            {
                "index": index,
                "title": heading,
                "score": score,
            }
        )

    strong_candidates = [entry for entry in candidates if entry["score"] >= 4]
    usable_candidates = [entry for entry in candidates if entry["score"] >= 3]
    loose_candidates = [entry for entry in candidates if entry["score"] >= 2]
    numeric_fallback = lambda: infer_numeric_structured_content_from_main_content(main_content_html)

    if len(usable_candidates) >= 2 and strong_candidates:
        selected_candidates = usable_candidates
        used_loose_fallback = False
    elif len(loose_candidates) >= 3:
        selected_candidates = loose_candidates
        used_loose_fallback = True
    else:
        return numeric_fallback()

    heading_index_map = {
        entry["index"]: entry["title"]
        for entry in selected_candidates
    }

    content_items = []
    current_section = None
    for index, block in enumerate(blocks):
        if block.parent is None:
            continue

        section_title = heading_index_map.get(index)
        if section_title:
            if current_section and plain_text_from_html("\n".join(current_section["content_parts"])):
                content_items.append(
                    {
                        "title": current_section["title"],
                        "content": "\n".join(current_section["content_parts"]).strip(),
                        "type": "lesson",
                        "parent": None,
                        "path": [current_section["title"]],
                    }
                )
            current_section = {"title": section_title, "content_parts": []}
            block.decompose()
            continue

        if current_section is not None:
            current_section["content_parts"].append(str(block))
            block.decompose()

    if current_section and plain_text_from_html("\n".join(current_section["content_parts"])):
        content_items.append(
            {
                "title": current_section["title"],
                "content": "\n".join(current_section["content_parts"]).strip(),
                "type": "lesson",
                "parent": None,
                "path": [current_section["title"]],
            }
        )

    if len(content_items) < 2:
        return numeric_fallback()

    if used_loose_fallback:
        substantive_sections = [
            item
            for item in content_items
            if len(clean_display_text(plain_text_from_html(item.get("content", "")))) >= 20
        ]
        if len(substantive_sections) < 2:
            return numeric_fallback()

    if len(content_items) < 2:
        return numeric_fallback()

    return build_flat_toc_from_content_items(content_items), content_items, str(soup)


def split_trailing_front_sections(main_content_html):
    if not main_content_html:
        return [], main_content_html

    soup = BeautifulSoup(main_content_html, "html.parser")
    blocks = [block for block in list(soup.find_all(BLOCK_TAG_NAMES)) if block.parent is not None]
    if not blocks:
        return [], main_content_html

    trailing_start_index = None
    has_content_before = False

    for index, block in enumerate(blocks):
        text = block_text(block)
        if not text:
            continue

        if resolve_front_section_title(block):
            suffix_has_body_heading = False
            for suffix_block in blocks[index + 1 :]:
                if suffix_block.parent is None:
                    continue
                suffix_title = block_heading_candidate_text(suffix_block)
                suffix_text = block_text(suffix_block)
                if suffix_title and not is_front_section_heading(suffix_title, tag_name=suffix_block.name):
                    suffix_has_body_heading = True
                    break
                if is_body_section_marker(suffix_text, tag_name=suffix_block.name) and not resolve_front_section_title(suffix_block):
                    suffix_has_body_heading = True
                    break
            if not suffix_has_body_heading and has_content_before:
                trailing_start_index = index
                break

        if plain_text_from_html(str(block)):
            has_content_before = True

    if trailing_start_index is None:
        return [], main_content_html

    sections = []
    current_section = None

    for block in blocks[trailing_start_index:]:
        if block.parent is None:
            continue

        text = block_text(block)
        if not text:
            continue

        section_title = resolve_front_section_title(block)
        if section_title:
            if current_section and plain_text_from_html("\n".join(current_section["html_parts"])):
                sections.append(
                    {
                        "title": current_section["title"],
                        "html": "\n".join(current_section["html_parts"]),
                    }
                )
            current_section = {"title": section_title, "html_parts": []}
            block.decompose()
            continue

        if is_separator_paragraph(text):
            block.decompose()
            continue
        if is_dot_bracketed_section_boundary(text):
            if current_section and plain_text_from_html("\n".join(current_section["html_parts"])):
                sections.append(
                    {
                        "title": current_section["title"],
                        "html": "\n".join(current_section["html_parts"]),
                    }
                )
            current_section = None
            block.decompose()
            continue

        if current_section is None:
            return [], main_content_html

        current_section["html_parts"].append(str(block))
        block.decompose()

    if current_section and plain_text_from_html("\n".join(current_section["html_parts"])):
        sections.append(
            {
                "title": current_section["title"],
                "html": "\n".join(current_section["html_parts"]),
            }
        )

    return sections, str(soup)


def extract_boundary_sections_from_content_items(content_items, toc, *, trust_source_toc=False):
    if not content_items:
        return [], [], toc or [], []

    normalized_items = [dict(item) for item in content_items]
    front_sections = []
    back_sections = []

    if not trust_source_toc:
        first_content = normalized_items[0].get("content", "")
        extracted_front_sections, cleaned_first_content = split_leading_front_sections(first_content)
        if extracted_front_sections:
            front_sections.extend(extracted_front_sections)
            normalized_items[0]["content"] = cleaned_first_content

        last_index = len(normalized_items) - 1
        last_content = normalized_items[last_index].get("content", "")
        extracted_back_sections, cleaned_last_content = split_trailing_front_sections(last_content)
        if extracted_back_sections:
            back_sections.extend(extracted_back_sections)
            normalized_items[last_index]["content"] = cleaned_last_content

    normalized_items = [
        item
        for item in normalized_items
        if plain_text_from_html(item.get("content", ""))
        or (item.get("has_content") is None and "has_content" in item and "source_url" in item)
    ]

    normalized_toc = toc or build_flat_toc_from_content_items(normalized_items)
    normalized_toc = prune_toc_entries_without_content(normalized_toc, normalized_items)
    return front_sections, back_sections, normalized_toc, normalized_items


def clean_extracted_dedication_html(dedication_html):
    if not dedication_html:
        return ""

    soup = BeautifulSoup(dedication_html, "html.parser")
    seen_heading = False

    for block in list(soup.find_all(BLOCK_TAG_NAMES)):
        if block.parent is None:
            continue

        text = block_text(block)
        if not text:
            block.decompose()
            continue

        strong_text = block_strong_text(block)
        is_heading = is_dedication_heading(text, strong_text=strong_text, tag_name=block.name)
        if is_heading:
            inline_dedication_text = strip_leading_dedication_label(text)
            if inline_dedication_text and inline_dedication_text != clean_display_text(text):
                block.clear()
                block.append(inline_dedication_text)
                text = block_text(block)
                strong_text = block_strong_text(block)
                is_heading = is_dedication_heading(text, strong_text=strong_text, tag_name=block.name)
        is_duplicate_heading = seen_heading and text_matches_patterns(text, DEDICATION_PATTERNS) and len(text) <= 40

        if is_separator_paragraph(text) or is_heading or is_duplicate_heading:
            seen_heading = seen_heading or is_heading
            block.decompose()
            continue

        break

    cleaned_html = str(soup).strip()
    return cleaned_html if plain_text_from_html(cleaned_html) else ""


# ---------------------------------------------------------------------------
# Phase A.2: Sub-chapter synthesis from in-chapter headings (h2/h3/h4)
# ---------------------------------------------------------------------------

SUBCHAPTER_HEADING_PREFERENCE = ("h2", "h3", "h4")
SUBCHAPTER_MIN_HEADINGS = 2
SUBCHAPTER_MIN_BODY_TEXT = 20
SUBCHAPTER_PARENT_INTRO_MIN_TEXT = 80


def _heading_is_top_level(heading_tag):
    parent = heading_tag.parent
    while parent is not None and parent.name is not None:
        if parent.name in {"blockquote", "table", "thead", "tbody", "tr", "td", "th", "figure", "aside"}:
            return False
        parent = parent.parent
    return True


def _collect_subchapter_candidates(content_html):
    if not content_html or not content_html.strip():
        return None, []

    soup = BeautifulSoup(content_html, "html.parser")
    for tag_name in SUBCHAPTER_HEADING_PREFERENCE:
        headings = [
            tag
            for tag in soup.find_all(tag_name)
            if _heading_is_top_level(tag) and clean_display_text(tag.get_text(" ", strip=True))
        ]
        if len(headings) >= SUBCHAPTER_MIN_HEADINGS:
            return soup, headings
    return None, []


def _split_html_by_headings(soup, headings):
    """Walk top-level children of the soup root and partition into:
    {preamble_html, sections=[{title, html}]}.
    Sections end at the next heading at the same level (or end of doc).
    """
    heading_ids = {id(tag) for tag in headings}
    title_by_id = {
        id(tag): clean_display_text(tag.get_text(" ", strip=True))
        for tag in headings
    }

    preamble_parts = []
    sections = []
    current = None
    # Iterate the soup's direct children plus any children of a wrapping container.
    # Use a flat list: every direct descendant of soup root.
    nodes = list(soup.children)

    def _walk(node_list):
        nonlocal current
        for node in list(node_list):
            if getattr(node, "name", None) is None:
                # NavigableString — assign to current section / preamble
                txt = str(node)
                if not txt.strip():
                    continue
                if current is None:
                    preamble_parts.append(txt)
                else:
                    current["html_parts"].append(txt)
                continue
            if id(node) in heading_ids:
                title = title_by_id[id(node)]
                current = {"title": title, "html_parts": []}
                sections.append(current)
                continue
            # If a non-heading element contains one of our headings, descend.
            nested = [
                child
                for child in node.find_all(SUBCHAPTER_HEADING_PREFERENCE)
                if id(child) in heading_ids
            ]
            if nested:
                _walk(list(node.children))
                continue
            html = str(node)
            if current is None:
                preamble_parts.append(html)
            else:
                current["html_parts"].append(html)

    _walk(nodes)

    return {
        "preamble_html": "\n".join(preamble_parts).strip(),
        "sections": [
            {"title": s["title"], "html": "\n".join(s["html_parts"]).strip()}
            for s in sections
        ],
    }


def _subchapter_titles_are_safe(sections):
    titles = [s["title"] for s in sections]
    if any(not title for title in titles):
        return False
    # All identical titles → not useful as TOC.
    if len(set(titles)) == 1:
        return False
    return True


def _split_content_item_into_subchapters(item):
    """Return (parent_item, sub_items) if the item can be split, else None."""
    content_html = item.get("content", "") or ""
    soup, headings = _collect_subchapter_candidates(content_html)
    if not soup or len(headings) < SUBCHAPTER_MIN_HEADINGS:
        return None

    partition = _split_html_by_headings(soup, headings)
    sections = partition["sections"]
    if len(sections) < SUBCHAPTER_MIN_HEADINGS:
        return None
    if not _subchapter_titles_are_safe(sections):
        return None

    # Every section must have at least SUBCHAPTER_MIN_BODY_TEXT of body content.
    for section in sections:
        text = clean_display_text(plain_text_from_html(section["html"]))
        if len(text) < SUBCHAPTER_MIN_BODY_TEXT:
            return None

    parent_title = item.get("title", "")
    parent_path = list(item.get("path") or [parent_title])
    preamble_html = partition["preamble_html"]
    preamble_text = clean_display_text(plain_text_from_html(preamble_html))
    keep_parent_intro = len(preamble_text) >= SUBCHAPTER_PARENT_INTRO_MIN_TEXT

    parent_item = {
        **item,
        "content": preamble_html if keep_parent_intro else "",
        "path": parent_path,
    }

    sub_items = []
    for section in sections:
        sub_path = parent_path + [section["title"]]
        sub_items.append(
            {
                "title": section["title"],
                "content": section["html"],
                "type": "topic",
                "parent": parent_title,
                "path": sub_path,
            }
        )
    return parent_item, sub_items, keep_parent_intro


def _find_toc_entry_by_path(toc_entries, path):
    target = list(path)
    for entry in toc_entries or []:
        entry_path = list(entry.get("path") or [entry.get("title", "")])
        if entry_path == target:
            return entry
        nested = _find_toc_entry_by_path(entry.get("children") or [], path)
        if nested is not None:
            return nested
    return None


def expand_content_items_with_subchapters(toc, content_items):
    """Synthesise nested sub-chapters from h2/h3/h4 inside top-level lessons.

    For every leaf content item that has 2+ same-level headings inside its
    HTML body, split it into:
      - an optional preamble (kept on the parent if substantial),
      - child topic items for each heading section.
    The matching TOC entry receives ``children`` mirroring the new structure.
    Items that already have explicit children (i.e. the curated source already
    declared a hierarchy) are left untouched.

    Returns (new_toc, new_content_items). Safe no-op when nothing to split.
    """
    if not content_items:
        return toc, content_items

    # Collect titles of items that have children declared elsewhere in toc — we
    # never split those. Build a set of TOC paths that already have children.
    paths_with_children = set()

    def _walk_toc(entries):
        for entry in entries or []:
            entry_path = tuple(entry.get("path") or [entry.get("title", "")])
            if entry.get("children"):
                paths_with_children.add(entry_path)
            _walk_toc(entry.get("children") or [])

    _walk_toc(toc or [])

    # Titles that already appear as parents in content_items (i.e. there are
    # children already in content_items pointing to them) should not be split.
    declared_parent_titles = {
        item.get("parent")
        for item in content_items
        if item.get("parent")
    }

    new_items = []
    # We mutate a deep-ish copy of toc to attach children.
    new_toc = [
        {**entry, "children": list(entry.get("children") or [])}
        for entry in (toc or [])
    ]

    for item in content_items:
        path = tuple(item.get("path") or [item.get("title", "")])
        title = item.get("title", "")
        # Skip items that are themselves children, or already have descendants.
        if item.get("parent"):
            new_items.append(item)
            continue
        if title in declared_parent_titles:
            new_items.append(item)
            continue
        if path in paths_with_children:
            new_items.append(item)
            continue

        split = _split_content_item_into_subchapters(item)
        if not split:
            new_items.append(item)
            continue

        parent_item, sub_items, keep_parent_intro = split
        new_items.append(parent_item)
        new_items.extend(sub_items)

        # Mirror the new structure into the TOC.
        toc_entry = _find_toc_entry_by_path(new_toc, list(path))
        children_entries = [
            {
                "title": sub["title"],
                "type": "topic",
                "has_content": True,
                "path": sub["path"],
            }
            for sub in sub_items
        ]
        if toc_entry is not None:
            toc_entry["children"] = children_entries
            toc_entry["has_content"] = bool(keep_parent_intro)
        else:
            # Item had no TOC entry — append one with children.
            new_toc.append(
                {
                    "title": title,
                    "type": "lesson",
                    "has_content": bool(keep_parent_intro),
                    "path": list(path),
                    "children": children_entries,
                }
            )

    return new_toc, new_items


# ---------------------------------------------------------------------------
# Residual main content classification
# ---------------------------------------------------------------------------
# When TOC + content_items capture the body of the book, anything left in the
# residual main content has to be classified into one of three buckets:
#   1. duplicate of existing content / empty   -> discard
#   2. key:value style metadata                -> merge into book_info
#   3. prose paragraph(s)                      -> wrap under a generated
#                                                 heading and add as a
#                                                 front section


RESIDUAL_SECTION_MIN_PLAIN_LENGTH = 24
RESIDUAL_HEADING_MAX_CHARS = 48
RESIDUAL_HEADING_MAX_WORDS = 8
# Empty string means "no explicit heading" — callers (normalize_body_sections)
# will assign a nav-only label (পূর্বকথা / Preliminary Note) so the page is
# reachable via the sidebar without displaying a heading on the page itself.
RESIDUAL_SECTION_FALLBACK_TITLE = ""


def _generate_residual_heading(plain_text):
    """Analyze a block of prose and produce a short, descriptive heading.

    Strategy: take the first sentence (split on Bengali দণ্ড / latin
    sentence terminators). If that is short enough use it verbatim,
    otherwise truncate to the first few words.
    """
    cleaned = clean_display_text(plain_text or "")
    if not cleaned:
        return RESIDUAL_SECTION_FALLBACK_TITLE
    first_sentence = re.split(r"[।.!?]", cleaned, maxsplit=1)[0].strip()
    candidate = first_sentence or cleaned
    if len(candidate) <= RESIDUAL_HEADING_MAX_CHARS:
        return candidate
    words = candidate.split()
    truncated_words = []
    running_length = 0
    for word in words:
        if (
            len(truncated_words) >= RESIDUAL_HEADING_MAX_WORDS
            or running_length + len(word) + 1 > RESIDUAL_HEADING_MAX_CHARS
        ):
            break
        truncated_words.append(word)
        running_length += len(word) + 1
    truncated = " ".join(truncated_words).rstrip(" -–—,:।")
    return truncated or RESIDUAL_SECTION_FALLBACK_TITLE


def classify_residual_main_content(
    residual_main_html,
    *,
    existing_fragments=None,
):
    """Classify residual main content into metadata / sections / discard.

    Returns ``(book_info_html, sections, remaining_residual_html)``.

    ``existing_fragments`` is an iterable of HTML strings whose block-level
    text should be treated as already-present (so any residual block that
    duplicates them is discarded).

    The returned remaining residual is always empty — every block has been
    accounted for. Anything that did not classify as metadata or prose is
    silently dropped.
    """
    if not residual_main_html or not plain_text_from_html(residual_main_html):
        return "", [], ""

    existing_signatures = collect_fragment_signatures(*(existing_fragments or []))

    soup = BeautifulSoup(residual_main_html, "html.parser")

    book_info_parts = []
    section_buckets = []
    current_bucket = None

    def _flush_current_bucket():
        nonlocal current_bucket
        if current_bucket and current_bucket["html_parts"]:
            section_buckets.append(current_bucket)
        current_bucket = None

    for block in list(soup.find_all(BLOCK_TAG_NAMES)):
        if block.parent is None:
            continue
        text = block_text(block)
        if not text:
            continue
        if is_separator_paragraph(text):
            _flush_current_bucket()
            continue

        signature = normalized_fragment_signature(text)
        if (
            signature
            and len(signature) >= MIN_DUPLICATE_FRAGMENT_SIGNATURE_LENGTH
            and signature in existing_signatures
        ):
            continue

        strong_text = block_strong_text(block)
        has_break = block_has_break(block)

        if search_front_matter_label_value(text, strong_text=strong_text, has_break=has_break):
            _flush_current_bucket()
            book_info_parts.append(str(block))
            if signature:
                existing_signatures.add(signature)
            continue

        if current_bucket is None:
            current_bucket = {"html_parts": [], "plain_parts": []}
        current_bucket["html_parts"].append(str(block))
        current_bucket["plain_parts"].append(text)
        if signature:
            existing_signatures.add(signature)

    _flush_current_bucket()

    sections = []
    for bucket in section_buckets:
        combined_plain = " ".join(bucket["plain_parts"]).strip()
        if len(clean_display_text(combined_plain)) < RESIDUAL_SECTION_MIN_PLAIN_LENGTH:
            continue
        html_parts = list(bucket["html_parts"])
        plain_parts = list(bucket["plain_parts"])
        heading = ""
        # Prefer using the first block as a heading only when it is
        # genuinely heading-shaped (short, few words, no sentence
        # terminator). This prevents fabricating phantom chapter titles
        # like an unrelated first-sentence excerpt from a paragraph.
        if html_parts and plain_parts:
            first_text = clean_display_text(plain_parts[0])
            if (
                first_text
                and len(first_text) <= RESIDUAL_HEADING_MAX_CHARS
                and len(first_text.split()) <= RESIDUAL_HEADING_MAX_WORDS
                and not re.search(r"[।.!?]", first_text)
            ):
                heading = first_text
                html_parts = html_parts[1:]
                plain_parts = plain_parts[1:]
        if not heading:
            heading = RESIDUAL_SECTION_FALLBACK_TITLE
        body_html = "\n".join(html_parts)
        if not plain_text_from_html(body_html):
            continue
        sections.append({"title": heading, "html": body_html})

    book_info_html = "\n".join(book_info_parts).strip()
    return book_info_html, sections, ""

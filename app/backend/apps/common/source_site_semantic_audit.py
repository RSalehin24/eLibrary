from collections import Counter

from apps.catalog.models import ContributorRole
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.services.normalization import (
    combined_front_matter_html,
    iter_front_matter_blocks,
    normalize_scraped_book,
)
from apps.ingestion.services.normalization_support.metadata import (
    clean_contributor_value,
    extract_contributor_evidence,
    is_role_label_text,
    looks_like_contributor_name,
    roles_in_text,
    split_contributor_value,
    split_metadata_fragments,
)


ROLE_HINTS = {
    ContributorRole.TRANSLATOR: (
        "অনুবাদ",
        "অনুবাদক",
        "ভাষান্তর",
        "রূপান্তর",
        "translator",
        "translation",
    ),
    ContributorRole.EDITOR: (
        "সম্পাদক",
        "সম্পাদনা",
        "সম্পাদিত",
        "সংকলক",
        "সংকলন",
        "compiled by",
        "compiler",
        "editor",
        "edited by",
    ),
    ContributorRole.PUBLISHER: (
        "প্রকাশক",
        "প্রকাশনী",
        "প্রকাশনা",
        "publisher",
        "published by",
    ),
    ContributorRole.COVER_ARTIST: (
        "প্রচ্ছদ",
        "cover",
    ),
    ContributorRole.ILLUSTRATOR: (
        "অলংকরণ",
        "illustration",
    ),
}


def path_tuple(path_value):
    if isinstance(path_value, (list, tuple)):
        return tuple(part for part in path_value if part)
    return ()


def resolve_toc_path(entry, parent_path=()):
    explicit_path = path_tuple(entry.get("path"))
    if explicit_path:
        return explicit_path
    return tuple(parent_path) + (entry.get("title", ""),)


def flatten_toc_paths(toc_entries, *, require_content=False, parent_path=()):
    paths = []
    for entry in toc_entries or []:
        path = resolve_toc_path(entry, parent_path)
        has_children = bool(entry.get("children"))
        if not require_content or entry.get("has_content") or not has_children:
            paths.append(path)
        paths.extend(
            flatten_toc_paths(
                entry.get("children", []),
                require_content=require_content,
                parent_path=path,
            )
        )
    return paths


def flatten_toc_leaf_paths(toc_entries, parent_path=()):
    paths = []
    for entry in toc_entries or []:
        path = resolve_toc_path(entry, parent_path)
        children = entry.get("children", [])
        if children:
            paths.extend(flatten_toc_leaf_paths(children, parent_path=path))
            continue
        paths.append(path)
    return paths


def flatten_content_paths(content_items):
    return [
        path_tuple(item.get("path"))
        for item in content_items or []
        if path_tuple(item.get("path"))
    ]


def canonical_role(role):
    if role == ContributorRole.COMPILER:
        return ContributorRole.EDITOR
    return role or ContributorRole.AUTHOR


def normalized_name(value):
    return normalize_catalog_text(clean_display_text(value))


def front_matter_block_rows(book_info_html="", main_content_html=""):
    combined_html = combined_front_matter_html(book_info_html, main_content_html)
    blocks = []
    for block in iter_front_matter_blocks(combined_html):
        if isinstance(block, str):
            text = clean_display_text(block)
            strong_text = ""
            if not text:
                continue
            blocks.append({"text": text, "strong_text": strong_text})
            continue

        if block.find("br") is not None:
            for line in block.get_text("\n", strip=True).splitlines():
                text = clean_display_text(line)
                if not text:
                    continue
                blocks.append({"text": text, "strong_text": ""})
            continue

        text = clean_display_text(block.get_text(" ", strip=True))
        strong_text = clean_display_text(
            " ".join(tag.get_text(" ", strip=True) for tag in block.find_all("strong"))
        )
        if not text:
            continue
        blocks.append({"text": text, "strong_text": strong_text})
    return blocks


def role_hints_for_text(text):
    normalized = normalize_catalog_text(text)
    if not normalized:
        return []

    hints = [canonical_role(role) for role in roles_in_text(text)]
    for role, keywords in ROLE_HINTS.items():
        if any(normalize_catalog_text(keyword) in normalized for keyword in keywords):
            hints.append(role)

    deduped = []
    seen = set()
    for role in hints:
        if role in seen:
            continue
        seen.add(role)
        deduped.append(role)
    return deduped


def cleaned_name_candidates(value, role=""):
    cleaned = clean_contributor_value(value)
    names = split_contributor_value(cleaned, role=role)
    if names:
        return names
    if looks_like_contributor_name(cleaned, role=role):
        return [cleaned]
    return []


def source_contributor_candidates(front_blocks, author_line=""):
    candidates = []
    seen = set()

    def add(name, role, evidence):
        normalized = normalized_name(name)
        key = (normalized, canonical_role(role))
        if not normalized or key in seen:
            return
        seen.add(key)
        candidates.append(
            {
                "name": clean_display_text(name),
                "role": canonical_role(role),
                "evidence": clean_display_text(evidence),
            }
        )

    for index, block in enumerate(front_blocks):
        text = block["text"]
        hinted_roles = role_hints_for_text(text)
        inline_evidence = extract_contributor_evidence(text, raw_value=text)
        for contributor in inline_evidence["contributors"]:
            add(contributor["name"], contributor["role"], text)

        if hinted_roles and not inline_evidence["contributors"] and is_role_label_text(text):
            for next_block in front_blocks[index + 1 : index + 3]:
                next_text = clean_display_text(next_block["text"])
                if not next_text:
                    continue
                if role_hints_for_text(next_text):
                    break
                primary_role = hinted_roles[0] if len(hinted_roles) == 1 else ""
                candidates_from_next = cleaned_name_candidates(next_text, role=primary_role)
                if not candidates_from_next:
                    break
                for role in hinted_roles:
                    for name in candidates_from_next:
                        add(name, role, f"{text} || {next_text}")
                break

    author_evidence = extract_contributor_evidence(author_line or "", raw_value=author_line or "")
    claimed_non_authors = {
        normalized_name(candidate["name"])
        for candidate in candidates
        if candidate["role"] != ContributorRole.AUTHOR
    }

    for author in author_evidence["authors"]:
        if normalized_name(author) in claimed_non_authors:
            continue
        add(author, ContributorRole.AUTHOR, author_line)
    for contributor in author_evidence["contributors"]:
        add(contributor["name"], contributor["role"], author_line)

    return candidates


def contributor_delta(scraped_data):
    front_blocks = front_matter_block_rows(
        scraped_data.get("book_info", ""),
        scraped_data.get("main_content", ""),
    )
    expected = source_contributor_candidates(front_blocks, scraped_data.get("author", ""))
    extracted = normalize_scraped_book(scraped_data).get("contributors", [])

    expected_map = {
        (normalized_name(candidate["name"]), canonical_role(candidate["role"])): candidate
        for candidate in expected
    }
    extracted_map = {
        (normalized_name(candidate["name"]), canonical_role(candidate["role"])): {
            **candidate,
            "role": canonical_role(candidate["role"]),
        }
        for candidate in extracted
    }

    missing = [
        candidate
        for key, candidate in expected_map.items()
        if key not in extracted_map
    ]
    unsupported = [
        candidate
        for key, candidate in extracted_map.items()
        if key not in expected_map
    ]

    return {
        "front_blocks": front_blocks,
        "expected_contributors": list(expected_map.values()),
        "extracted_contributors": list(extracted_map.values()),
        "missing_contributors": missing,
        "unsupported_contributors": unsupported,
        "has_deltas": bool(missing or unsupported),
    }


def structure_delta(scraped_data):
    toc = scraped_data.get("toc", []) or []
    content_items = scraped_data.get("content_items", []) or []

    content_paths = flatten_content_paths(content_items)
    content_counter = Counter(content_paths)

    if not toc:
        return {
            "duplicate_content_paths": [],
            "dead_toc_paths": [],
            "missing_toc_paths_for_content": [],
            "duplicate_toc_paths": [],
            "has_deltas": False,
        }

    toc_paths = flatten_toc_paths(toc, require_content=True)
    toc_counter = Counter(toc_paths)

    content_path_set = set(content_paths)
    toc_path_set = set(toc_paths)
    dead_toc_paths = sorted(
        [list(path) for path in set(flatten_toc_leaf_paths(toc)) - content_path_set]
    )
    missing_toc_paths_for_content = sorted(
        [list(path) for path in content_path_set - toc_path_set]
    )
    count_mismatch_paths = [
        list(path)
        for path in sorted(set(content_counter) | set(toc_counter))
        if content_counter.get(path, 0) != toc_counter.get(path, 0)
    ]

    return {
        "duplicate_content_paths": count_mismatch_paths,
        "dead_toc_paths": dead_toc_paths,
        "missing_toc_paths_for_content": missing_toc_paths_for_content,
        "duplicate_toc_paths": count_mismatch_paths,
        "has_deltas": bool(
            count_mismatch_paths
            or dead_toc_paths
            or missing_toc_paths_for_content
        ),
    }


def audit_scraped_book(scraped_data):
    contributor_report = contributor_delta(scraped_data)
    structure_report = structure_delta(scraped_data)
    return {
        **contributor_report,
        **structure_report,
        "has_deltas": contributor_report["has_deltas"] or structure_report["has_deltas"],
    }

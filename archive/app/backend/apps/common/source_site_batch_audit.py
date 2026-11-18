import json
from pathlib import Path
from urllib.parse import quote, urljoin

import requests

from apps.catalog.models import GeneratedAssetType
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.services.legacy_adapter import scrape_book_high_fidelity
from apps.ingestion.services.normalization import (
    combined_front_matter_html,
    extract_front_matter_entries,
    normalize_scraped_book,
    promote_leading_front_matter,
)
from apps.ingestion.services.resolution import TitleResolver, fetch_source_page_metadata

REQUIRED_PRODUCTION_ASSET_TYPES = {
    GeneratedAssetType.HTML,
    GeneratedAssetType.EPUB,
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
        if not require_content or entry.get("has_content") or has_children:
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


def contributor_role_map(contributors):
    role_map = {}
    for contributor in contributors or []:
        name = clean_display_text(contributor.get("name", ""))
        role = contributor.get("role", "")
        normalized_name = normalize_catalog_text(name)
        if not normalized_name or not role:
            continue
        role_map.setdefault(normalized_name, {"display_name": name, "roles": set()})
        role_map[normalized_name]["roles"].add(role)
    return role_map


def compare_contributors(source_contributors, production_contributors):
    source_map = contributor_role_map(source_contributors)
    production_map = contributor_role_map(production_contributors)

    role_mismatches = []
    missing = []
    polluted = []

    for normalized_name, source_entry in source_map.items():
        production_entry = production_map.get(normalized_name)
        if production_entry is None:
            missing.append(
                {
                    "name": source_entry["display_name"],
                    "roles": sorted(source_entry["roles"]),
                }
            )
            continue
        if source_entry["roles"] != production_entry["roles"]:
            role_mismatches.append(
                {
                    "name": source_entry["display_name"],
                    "source_roles": sorted(source_entry["roles"]),
                    "production_roles": sorted(production_entry["roles"]),
                }
            )

    for normalized_name, production_entry in production_map.items():
        if normalized_name in source_map:
            continue
        polluted.append(
            {
                "name": production_entry["display_name"],
                "roles": sorted(production_entry["roles"]),
            }
        )

    return {
        "role_mismatches": role_mismatches,
        "missing_contributors": missing,
        "polluted_contributors": polluted,
    }


def compare_toc_and_content(source_report, production_detail):
    source_toc_paths = set(flatten_toc_paths(source_report.get("toc", []), require_content=True))
    source_content_paths = set(flatten_content_paths(source_report.get("content_items", [])))
    production_toc = production_detail.get("toc", []) if isinstance(production_detail, dict) else []
    production_raw_payload = (
        ((production_detail.get("raw_provenance") or {}).get("raw_scrape_payload"))
        if isinstance(production_detail, dict)
        else {}
    ) or {}
    production_content_items = production_raw_payload.get("content_items", []) if isinstance(production_raw_payload, dict) else []
    production_toc_paths = set(flatten_toc_paths(production_toc, require_content=True))
    production_content_paths = set(flatten_content_paths(production_content_items))
    production_dead_toc = sorted(
        list(set(flatten_toc_leaf_paths(production_toc)) - production_content_paths)
    )

    return {
        "missing_toc_paths": sorted(list(source_toc_paths - production_toc_paths)),
        "missing_content_paths": sorted(list(source_content_paths - production_content_paths)),
        "production_dead_toc_paths": production_dead_toc,
        "production_raw_provenance_present": bool(production_detail.get("raw_provenance")) if isinstance(production_detail, dict) else False,
    }


def compare_assets(source_report, production_detail):
    production_assets = production_detail.get("assets", []) if isinstance(production_detail, dict) else []
    ready_assets = {
        asset.get("asset_type")
        for asset in production_assets
        if asset.get("status") == "ready"
    }
    expected_assets = set(REQUIRED_PRODUCTION_ASSET_TYPES)
    if source_report.get("cover_expected"):
        expected_assets.add(GeneratedAssetType.COVER)
    return {
        "missing_ready_assets": sorted(list(expected_assets - ready_assets)),
    }


def build_source_report(source_entry, *, source_page_metadata=None):
    metadata = source_page_metadata or fetch_source_page_metadata(source_entry.source_url)
    scraped_data = scrape_book_high_fidelity(source_entry.source_url)
    if not isinstance(scraped_data, dict):
        raise ValueError(f"High-fidelity scrape failed for {source_entry.source_url}")

    promoted_book_info, cleaned_main_content = promote_leading_front_matter(
        scraped_data.get("book_info", ""),
        scraped_data.get("main_content", ""),
    )
    scraped_data["book_info"] = promoted_book_info
    scraped_data["main_content"] = cleaned_main_content

    normalized = normalize_scraped_book(scraped_data)
    front_matter_html = combined_front_matter_html(
        scraped_data.get("book_info", ""),
        scraped_data.get("main_content", ""),
    )
    return {
        "source_url": source_entry.source_url,
        "source_entry_id": str(source_entry.id),
        "catalog_metadata": source_entry.raw_data if isinstance(source_entry.raw_data, dict) else {},
        "page_metadata": metadata.get("raw_data", {}),
        "book_title": scraped_data.get("book_title", ""),
        "raw_author": scraped_data.get("author", ""),
        "series": scraped_data.get("series", ""),
        "book_type": scraped_data.get("book_type", ""),
        "cover_expected": bool(scraped_data.get("cover")),
        "front_matter_entries": extract_front_matter_entries(front_matter_html),
        "contributors": normalized.get("contributors", []),
        "toc": scraped_data.get("toc", []),
        "content_items": scraped_data.get("content_items", []),
        "toc_paths": [list(path) for path in flatten_toc_paths(scraped_data.get("toc", []), require_content=True)],
        "content_paths": [list(path) for path in flatten_content_paths(scraped_data.get("content_items", []))],
    }


def build_production_session(cookie_header=""):
    session = requests.Session()
    if cookie_header:
        session.headers.update({"Cookie": cookie_header})
    session.headers.update({"Accept": "application/json"})
    return session


def fetch_production_book_index(base_url, session, *, page_limit=100):
    base_url = base_url.rstrip("/")
    page = 1
    indexed = {}

    while True:
        response = session.get(
            urljoin(base_url, "/api/catalog/books/"),
            params={
                "record_type": "all",
                "limit": page_limit,
                "page": page,
                "sort": "title",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        entries = payload.get("entries", payload if isinstance(payload, list) else [])
        if not entries:
            break

        for entry in entries:
            primary_source = entry.get("primary_source") or {}
            source_url = clean_display_text(primary_source.get("url", ""))
            if not source_url:
                continue
            indexed[source_url] = entry

        pagination = payload.get("pagination", {}) if isinstance(payload, dict) else {}
        if not pagination.get("has_next"):
            break
        page += 1

    return indexed


def fetch_production_book_detail(base_url, session, slug):
    response = session.get(
        urljoin(base_url.rstrip("/"), f"/api/catalog/books/{quote(slug, safe='')}/"),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def compare_source_report_to_production(source_report, production_detail):
    if not production_detail:
        return {
            "source_url": source_report["source_url"],
            "production_missing": True,
            "role_mismatches": [],
            "missing_contributors": [],
            "polluted_contributors": [],
            "missing_toc_paths": [],
            "missing_content_paths": [],
            "production_dead_toc_paths": [],
            "missing_ready_assets": [],
            "has_deltas": True,
        }

    contributor_delta = compare_contributors(
        source_report.get("contributors", []),
        production_detail.get("contributors", []),
    )
    toc_delta = compare_toc_and_content(source_report, production_detail)
    asset_delta = compare_assets(source_report, production_detail)

    comparison = {
        "source_url": source_report["source_url"],
        "production_missing": False,
        **contributor_delta,
        **toc_delta,
        **asset_delta,
    }
    comparison["has_deltas"] = any(
        comparison[key]
        for key in (
            "role_mismatches",
            "missing_contributors",
            "polluted_contributors",
            "missing_toc_paths",
            "missing_content_paths",
            "production_dead_toc_paths",
            "missing_ready_assets",
        )
    )
    return comparison


def iter_sharded_source_entries(*, shard_count=1, shard_index=0, limit=None):
    queryset = SourceCatalogEntry.objects.order_by("source_url")
    if isinstance(limit, int) and limit > 0:
        queryset = queryset[:limit]

    for index, entry in enumerate(queryset):
        if index % max(1, shard_count) != shard_index:
            continue
        yield entry


def refresh_source_archive(*, max_pages=None, bucket=""):
    resolver = TitleResolver()
    resolver.refresh_catalog(max_pages=max_pages, bucket=bucket)
    return resolver


def ensure_report_dir(report_dir):
    path = Path(report_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_jsonl(path, rows):
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")

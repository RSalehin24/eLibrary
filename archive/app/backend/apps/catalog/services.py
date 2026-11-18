from apps.ingestion.services.resolution_support_hosts import get_source_site_domain

from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    BookSource,
    build_book_catalog_code,
    Category,
    Contributor,
    ContributorRole,
    is_entity_catalog_code,
    CATEGORY_ENTITY_TAG,
    WRITER_ENTITY_TAG,
    Series,
)
from apps.common.text import clean_entity_display_text, normalize_catalog_text


def canonical_display_name(value):
    return clean_entity_display_text(value)


def canonical_contributor_role(role):
    return role or ContributorRole.AUTHOR


def normalize_book_contributors(contributors):
    normalized_entries = []
    seen = set()
    non_author_names = set()

    for contributor_info in contributors or []:
        name = canonical_display_name(contributor_info.get("name", ""))
        role = canonical_contributor_role(
            contributor_info.get("role", ContributorRole.AUTHOR)
        )
        normalized_name = normalize_catalog_text(name)
        contributor_key = (normalized_name, role)
        if not normalized_name or contributor_key in seen:
            continue
        seen.add(contributor_key)
        normalized_entry = {
            **contributor_info,
            "name": name,
            "role": role,
        }
        normalized_entries.append(normalized_entry)
        if role != ContributorRole.AUTHOR:
            non_author_names.add(normalized_name)

    if not non_author_names:
        return normalized_entries

    return [
        entry
        for entry in normalized_entries
        if not (
            entry["role"] == ContributorRole.AUTHOR
            and normalize_catalog_text(entry["name"]) in non_author_names
        )
    ]


def get_or_create_contributor(name):
    cleaned = canonical_display_name(name)
    normalized = normalize_catalog_text(cleaned)
    if not normalized:
        return None
    contributor, _ = Contributor.objects.get_or_create(
        normalized_name=normalized,
        defaults={"name": cleaned},
    )
    if contributor.name != cleaned:
        contributor.name = cleaned
        contributor.save(update_fields=["name", "normalized_name", "slug", "catalog_code", "updated_at"])
    if not contributor.catalog_code or not is_entity_catalog_code(
        contributor.catalog_code,
        entity_tag=WRITER_ENTITY_TAG,
    ):
        contributor.save()
    return contributor


def get_or_create_series(name):
    cleaned = canonical_display_name(name)
    normalized = normalize_catalog_text(cleaned)
    if not normalized:
        return None
    series, _ = Series.objects.get_or_create(
        normalized_name=normalized,
        defaults={"name": cleaned},
    )
    return series


def get_or_create_category(name):
    cleaned = canonical_display_name(name)
    normalized = normalize_catalog_text(cleaned)
    if not normalized:
        return None
    category, _ = Category.objects.get_or_create(
        normalized_name=normalized,
        defaults={"name": cleaned},
    )
    if not category.catalog_code or not is_entity_catalog_code(
        category.catalog_code,
        entity_tag=CATEGORY_ENTITY_TAG,
    ):
        category.save()
    return category


def normalized_book_title(value):
    return normalize_catalog_text(value)


def find_existing_book_by_title(title):
    normalized = normalized_book_title(title)
    if not normalized:
        return None
    source_site = get_source_site_domain()
    return (
        Book.objects.filter(
            source_site=source_site,
            normalized_title=normalized,
            deleted_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )


def find_deleted_book_by_title(title):
    normalized = normalized_book_title(title)
    if not normalized:
        return None
    source_site = get_source_site_domain()
    return (
        Book.objects.filter(
            source_site=source_site,
            normalized_title=normalized,
            deleted_at__isnull=False,
        )
        .order_by("-deleted_at", "-created_at")
        .first()
    )


def find_existing_book_by_source_url(normalized_source_url):
    source = (
        BookSource.objects.select_related("book")
        .filter(normalized_source_url=normalized_source_url, book__deleted_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    return source.book if source else None


def sync_book_catalog_code(book):
    if not book.pk:
        book.save()
        return book

    next_code = build_book_catalog_code(book)
    if next_code != book.catalog_code:
        book.catalog_code = next_code
        book.save(update_fields=["catalog_code", "updated_at"])
    return book


def replace_book_relations(book, contributors=None, series_names=None, category_names=None):
    if contributors is not None:
        book.book_contributors.all().delete()
        seen_contributors = set()
        for index, contributor_info in enumerate(normalize_book_contributors(contributors)):
            contributor = get_or_create_contributor(contributor_info["name"])
            if contributor is None:
                continue
            contributor_key = (contributor.pk, contributor_info["role"])
            if contributor_key in seen_contributors:
                continue
            seen_contributors.add(contributor_key)
            BookContributor.objects.update_or_create(
                book=book,
                contributor=contributor,
                role=contributor_info["role"],
                defaults={
                    "raw_value": contributor_info.get("raw_value", contributor_info["name"]),
                    "sort_order": index,
                },
            )

    if series_names is not None:
        book.book_series.all().delete()
        seen_series = set()
        for index, series_name in enumerate(series_names):
            normalized_name = normalize_catalog_text(series_name)
            if not normalized_name or normalized_name in seen_series:
                continue
            seen_series.add(normalized_name)
            series = get_or_create_series(series_name)
            if series is None:
                continue
            if series.pk in seen_series:
                continue
            seen_series.add(series.pk)
            BookSeries.objects.update_or_create(
                book=book,
                series=series,
                defaults={
                    "raw_value": series_name,
                    "sort_order": index,
                },
            )

    if category_names is not None:
        book.book_categories.all().delete()
        seen_categories = set()
        for category_name in category_names:
            normalized_name = normalize_catalog_text(category_name)
            if not normalized_name or normalized_name in seen_categories:
                continue
            seen_categories.add(normalized_name)
            category = get_or_create_category(category_name)
            if category is None:
                continue
            if category.pk in seen_categories:
                continue
            seen_categories.add(category.pk)
            BookCategory.objects.update_or_create(
                book=book,
                category=category,
                defaults={
                    "raw_value": category_name,
                },
            )

    sync_book_catalog_code(book)
    return book

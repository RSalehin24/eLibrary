import json

from apps.accounts.models import User
from apps.catalog.editorial.service import EditorialConflict, revision_checked_book
from apps.catalog.locking import lock_entity_kind, lock_title
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookGroup,
    BookSeries,
    Category,
    Contributor,
    MetadataVersion,
    Series,
)
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError


def related_editions(book):
    if book.group_id is None:
        return []
    return list(
        Book.objects.filter(group_id=book.group_id, deleted_at__isnull=True)
        .exclude(pk=book.pk)
        .values("id", "catalog_code", name=F("title"))
        .order_by("name", "id")[:101]
    )


def relationship_details(book):
    editions = related_editions(book)
    return {
        "id": book.pk,
        "updated_at": book.updated_at,
        "group_id": book.group_id,
        **relationship_selection(book),
        "related_editions": editions[:100],
        "has_more_editions": len(editions) > 100,
    }


def relationship_selection(book):
    return {
        "contributors": [
            {"id": identifier, "name": name, "catalog_code": code, "role": role}
            for identifier, name, code, role in book.book_contributors.order_by(
                "sort_order", "id"
            ).values_list(
                "contributor_id",
                "contributor__name",
                "contributor__catalog_code",
                "role",
            )
        ],
        "categories": related_references(book.book_categories.all(), "category"),
        "series": related_references(
            book.book_series.order_by("sort_order", "id"), "series"
        ),
    }


def related_references(links, field):
    return [
        {"id": identifier, "name": name, "catalog_code": code}
        for identifier, name, code in links.values_list(
            f"{field}_id", f"{field}__name", f"{field}__catalog_code"
        )
    ]


def record_relationship_version(actor, book, edit_note=""):
    details = relationship_selection(book)
    MetadataVersion.objects.create(
        book=book,
        created_by=actor,
        source="editorial-relationships",
        notes=edit_note,
        snapshot={
            "contributors": [
                {"id": str(entry["id"]), "role": entry["role"]}
                for entry in details["contributors"]
            ],
            "category_ids": [str(entry["id"]) for entry in details["categories"]],
            "series_ids": [str(entry["id"]) for entry in details["series"]],
            "group_id": str(book.group_id) if book.group_id else None,
        },
    )


def save_relationship_revision(book):
    book.save(update_fields=["group", "metadata_overrides", "updated_at"])


def require_available_references(model, identifiers, field):
    if model.objects.filter(pk__in=set(identifiers)).count() != len(set(identifiers)):
        raise ValidationError(
            {field: "One or more selected references are unavailable."}
        )


def replace_contributors(book, entries):
    require_available_references(
        Contributor, [entry["id"] for entry in entries], "contributors"
    )
    book.book_contributors.all().delete()
    BookContributor.objects.bulk_create(
        [
            BookContributor(
                book=book,
                contributor_id=entry["id"],
                role=entry["role"],
                sort_order=index,
            )
            for index, entry in enumerate(entries)
        ]
    )


def replace_categories(book, identifiers):
    require_available_references(Category, identifiers, "category_ids")
    book.book_categories.all().delete()
    BookCategory.objects.bulk_create(
        [BookCategory(book=book, category_id=identifier) for identifier in identifiers]
    )


def replace_series(book, identifiers):
    require_available_references(Series, identifiers, "series_ids")
    book.book_series.all().delete()
    BookSeries.objects.bulk_create(
        [
            BookSeries(book=book, series_id=identifier, sort_order=index)
            for index, identifier in enumerate(identifiers)
        ]
    )


def assign_edition(actor, book, identifier):
    if identifier is None:
        book.group_id = None
        return
    if identifier == book.pk:
        raise ValidationError({"edition_of": "Choose a different edition."})
    sibling = get_object_or_404(
        Book.objects.select_for_update(), pk=identifier, deleted_at__isnull=True
    )
    if sibling.group_id is None:
        record_relationship_version(actor, sibling)
        sibling.group = BookGroup.objects.create(canonical_title=sibling.title)
        save_relationship_revision(sibling)
    book.group_id = sibling.group_id


@transaction.atomic
def update_relationships(actor, book_id, attributes):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    # Edition commands can touch two books; serialize them before taking row locks.
    lock_title("catalog-book-relationships")
    for kind in ("categories", "contributors", "series"):
        lock_entity_kind(kind)
    book = revision_checked_book(actor, book_id, attributes["expected_updated_at"])
    if book.updated_at != attributes["expected_updated_at"]:
        raise EditorialConflict()
    record_relationship_version(actor, book, attributes.get("edit_note", ""))
    apply_relationships(actor, book, attributes)
    override_fields = {
        key: value
        for key, value in attributes.items()
        if key not in {"expected_updated_at", "edit_note"}
    }
    book.metadata_overrides = {
        **book.metadata_overrides,
        **json.loads(json.dumps(override_fields, cls=DjangoJSONEncoder)),
    }
    save_relationship_revision(book)
    return book


def apply_relationships(actor, book, attributes):
    for field, operation in [
        ("contributors", replace_contributors),
        ("category_ids", replace_categories),
        ("series_ids", replace_series),
    ]:
        if field in attributes:
            operation(book, attributes[field])
    if "edition_of" in attributes:
        assign_edition(actor, book, attributes["edition_of"])

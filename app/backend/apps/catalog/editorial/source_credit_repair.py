"""Audit and reverse a bounded correction without removing books or identities."""

from dataclasses import dataclass

from apps.catalog.editorial.relationships import record_relationship_version
from apps.catalog.models import Book, BookContributor, Contributor
from apps.common.models import AuditLog
from apps.ingestion.services.normalization import normalize_scraped_book
from apps.ingestion.services.source_credits import (
    NON_CREDIT_PHRASES,
    VERIFIED_CREDIT_NAMES,
    VERIFIED_ROLE_ALIASES,
    credit_identity,
    repairable_credit_names,
)
from django.db import transaction
from django.utils import timezone


@dataclass(frozen=True)
class CreditChange:
    link: BookContributor
    name: str | None
    role: str


def credit_repair_plan(book: Book) -> list[CreditChange]:
    payload = {
        **book.raw_scrape_payload,
        "book_info": book.book_info_html
        or book.raw_scrape_payload.get("book_info", ""),
    }
    expected = normalize_scraped_book(payload)["contributors"]
    return [
        change
        for link in book.book_contributors.select_related("contributor").all()
        if (change := credit_change(link, expected)) is not None
    ]


def credit_change(link: BookContributor, expected: list[dict]) -> CreditChange | None:
    name = link.contributor.name
    if name not in repairable_credit_names():
        return None
    if name in NON_CREDIT_PHRASES and link.role == "publisher":
        return CreditChange(link, None, link.role)
    canonical = VERIFIED_CREDIT_NAMES.get(name, name.removeprefix("এর জনাব "))
    for entry in expected:
        if credit_identity(entry["name"]) != credit_identity(canonical):
            continue
        if entry["role"] != link.role and not (
            name in VERIFIED_ROLE_ALIASES and link.role == "author"
        ):
            continue
        if entry["name"] != name or entry["role"] != link.role:
            return CreditChange(link, entry["name"], entry["role"])
    return None


def credit_snapshot(book: Book) -> list[dict]:
    return [
        {
            "id": str(link.pk),
            "contributor_id": str(link.contributor_id),
            "role": link.role,
            "raw_value": link.raw_value,
            "sort_order": link.sort_order,
        }
        for link in book.book_contributors.order_by("id")
    ]


def apply_credit_change(change: CreditChange) -> None:
    link = change.link
    if change.name is None:
        link.delete()
        return
    contributor, _ = Contributor.objects.get_or_create(name=change.name)
    duplicate = BookContributor.objects.filter(
        book_id=link.book_id, contributor=contributor, role=change.role
    ).exclude(pk=link.pk)
    if duplicate.exists():
        link.delete()
        return
    link.contributor, link.role = contributor, change.role
    link.save(update_fields=["contributor", "role", "updated_at"])


@transaction.atomic
def apply_credit_repair(book_id) -> AuditLog | None:
    book = Book.objects.select_for_update().get(pk=book_id)
    if not book.raw_scrape_payload:
        return None
    changes = credit_repair_plan(book)
    if not changes:
        return None
    before = credit_snapshot(book)
    record_relationship_version(
        None, book, "Automatic correction from explicit source credits."
    )
    for change in changes:
        apply_credit_change(change)
    Book.objects.filter(pk=book.pk).update(updated_at=timezone.now())
    return AuditLog.objects.create(
        verb="catalog.source_credit_repair",
        target_type="book",
        target_id=str(book.pk),
        payload={"before": before, "after": credit_snapshot(book)},
    )


@transaction.atomic
def restore_credit_repair(audit_id) -> AuditLog:
    audit = AuditLog.objects.get(pk=audit_id, verb="catalog.source_credit_repair")
    book = Book.objects.select_for_update().get(pk=audit.target_id)
    if credit_snapshot(book) != audit.payload["after"]:
        raise ValueError(
            "Book credits changed after the repair; restoration was not applied."
        )
    record_relationship_version(
        None, book, "Restore source credits from a recorded repair."
    )
    for entry in audit.payload["before"]:
        fields = {key: value for key, value in entry.items() if key != "id"}
        BookContributor.objects.update_or_create(
            pk=entry["id"], defaults={"book": book, **fields}
        )
    Book.objects.filter(pk=book.pk).update(updated_at=timezone.now())
    return AuditLog.objects.create(
        verb="catalog.source_credit_restore",
        target_type="book",
        target_id=str(book.pk),
        payload={
            "repair_id": str(audit.pk),
            "before": audit.payload["after"],
            "after": credit_snapshot(book),
        },
    )

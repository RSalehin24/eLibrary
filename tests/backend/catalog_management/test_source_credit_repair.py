from io import StringIO

import pytest
from apps.catalog.editorial.source_credit_repair import (
    apply_credit_repair,
    credit_repair_plan,
    credit_snapshot,
    restore_credit_repair,
)
from apps.catalog.models import Book, BookContributor, Contributor, GeneratedAsset
from apps.common.models import AuditLog
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db


def credit(book, name, role):
    contributor, _ = Contributor.objects.get_or_create(name=name)
    return BookContributor.objects.create(
        book=book, contributor=contributor, role=role, raw_value=name
    )


@pytest.fixture
def source_book():
    book = Book.objects.create(
        title="Verified source credits",
        state="published",
        raw_scrape_payload={
            "author": "জেমস রোলিন্স, সাঈম শামস",
            "book_info": "<p>অনুবাদক: সাঈম শামস্</p>",
        },
    )
    credit(book, "জেমস রোলিন্স", "author")
    credit(book, "সাঈম শামস", "author")
    credit(book, "সাঈম শামস্", "translator")
    return book


def test_repair_preserves_book_files_identities_and_can_restore_exact_relationships(
    source_book,
):
    asset = GeneratedAsset.objects.create(
        book=source_book, asset_type="epub", legacy_path="preserved.epub"
    )
    before = credit_snapshot(source_book)
    identities = set(Contributor.objects.values_list("pk", flat=True))
    original_slug = source_book.slug
    assert len(credit_repair_plan(source_book)) == 1
    audit = apply_credit_repair(source_book.pk)
    assert audit.verb == "catalog.source_credit_repair"
    assert source_book.book_contributors.count() == 2
    assert set(Contributor.objects.values_list("pk", flat=True)) == identities
    assert apply_credit_repair(source_book.pk) is None
    source_book.refresh_from_db()
    assert (source_book.slug, source_book.state) == (original_slug, "published")
    assert not hasattr(source_book, "review_state")
    asset.refresh_from_db()
    assert asset.legacy_path == "preserved.epub"
    restore_credit_repair(audit.pk)
    assert credit_snapshot(source_book) == before
    assert AuditLog.objects.filter(verb="catalog.source_credit_restore").count() == 1


def test_restoration_refuses_to_overwrite_later_credit_edits(source_book):
    audit = apply_credit_repair(source_book.pk)
    credit(source_book, "Another editor", "editor")
    edited = credit_snapshot(source_book)
    with pytest.raises(ValueError, match="changed after the repair"):
        restore_credit_repair(audit.pk)
    assert credit_snapshot(source_book) == edited


def test_command_defaults_to_dry_run_and_records_explicitly_applied_changes(
    source_book,
):
    output = StringIO()
    before = credit_snapshot(source_book)
    call_command("repair_source_credits", book=[str(source_book.pk)], stdout=output)
    assert "Proposed books: 1" in output.getvalue()
    assert credit_snapshot(source_book) == before
    assert AuditLog.objects.count() == 0
    call_command(
        "repair_source_credits", apply=True, book=[str(source_book.pk)], stdout=output
    )
    audit = AuditLog.objects.get(verb="catalog.source_credit_repair")
    with pytest.raises(CommandError, match="requires --apply"):
        call_command("repair_source_credits", restore=str(audit.pk))
    call_command(
        "repair_source_credits", apply=True, restore=str(audit.pk), stdout=output
    )
    assert credit_snapshot(source_book) == before


def test_cover_correction_retains_raw_credit_and_the_original_contributor_record():
    raw = "বিদেশি ছবি অবলম্বনে কোলায বনবীর আহমেদ বিতর"
    book = Book.objects.create(
        title="Cover credit", raw_scrape_payload={"book_info": f"<p>প্রচ্ছদ: {raw}</p>"}
    )
    link = credit(book, raw, "cover_artist")
    original_identity = link.contributor_id
    assert apply_credit_repair(book.pk) is not None
    link.refresh_from_db()
    assert link.contributor.name == "বনবীর আহমেদ"
    assert link.raw_value == raw
    assert Contributor.objects.filter(pk=original_identity).exists()


def test_manual_metadata_and_similar_names_are_not_rewritten():
    book = Book.objects.create(title="Manual book")
    credit(book, "সাঈম শামস", "author")
    assert apply_credit_repair(book.pk) is None
    assert book.book_contributors.count() == 1


def test_repair_reads_persisted_front_matter_when_the_payload_is_slim(source_book):
    source_book.book_info_html = source_book.raw_scrape_payload.pop("book_info")
    source_book.save(
        update_fields=["raw_scrape_payload", "book_info_html", "updated_at"]
    )
    assert len(credit_repair_plan(source_book)) == 1
    assert apply_credit_repair(source_book.pk) is not None
    assert source_book.book_contributors.filter(role="author").count() == 1

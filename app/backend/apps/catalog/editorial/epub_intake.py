from apps.accounts.models import User
from apps.catalog.editorial.creation import created_book
from apps.catalog.editorial.epub_uploads import (
    activate_uploaded_assets,
    prepare_uploaded_assets,
    upload_checksum,
    uploaded_storage_guard,
)
from apps.catalog.editorial.service import EditorialConflict
from apps.catalog.models import Book
from django.db import transaction


@transaction.atomic
def intake_revision(actor, command, checksum):
    identifier, expected = command
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    created = created_book(actor, identifier)
    book = Book.objects.select_for_update().get(pk=created.pk)
    asset = book.generated_assets.filter(asset_type="epub").first()
    if book.state == "published" and asset and asset.checksum == checksum:
        return book, True
    if (
        book.state != "draft"
        or book.generated_assets.exists()
        or book.source_urls.exists()
    ):
        raise EditorialConflict(
            "This intake is complete. Only an administrator can replace its files."
        )
    if book.updated_at != expected:
        raise EditorialConflict()
    return book, False


@transaction.atomic
def commit_intake(actor, command, staged):
    book, replayed = intake_revision(actor, command, staged[0].checksum)
    return book if replayed else activate_uploaded_assets(actor, book, staged)


def upload_created_epub(actor, identifier, values):
    with uploaded_storage_guard():
        command = identifier, values["expected_updated_at"]
        book, replayed = intake_revision(
            actor, command, upload_checksum(values["file"])
        )
        if replayed:
            return book
        staged = prepare_uploaded_assets(book, values["file"])
        return commit_intake(actor, command, staged)

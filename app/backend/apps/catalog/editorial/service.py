from apps.accounts.models import User
from apps.catalog.discovery.management import metadata_managed_books
from apps.catalog.models import Book, MetadataVersion
from apps.catalog.serializers.editorial import EDITORIAL_FIELDS
from apps.catalog.serializers.formats import BOOK_FORMAT_FIELDS
from apps.common.models import LifecycleState
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException


class EditorialConflict(APIException):
    status_code = 409
    default_code = "state_conflict"
    default_detail = "The book changed. Refresh its metadata before continuing."


def revision_checked_book(user, book_id, expected_updated_at):
    user = User.objects.select_for_update(no_key=True).get(pk=user.pk)
    book = get_object_or_404(
        Book.objects.filter(
            pk__in=metadata_managed_books(user).values("pk")
        ).select_for_update(),
        pk=book_id,
    )
    if book.updated_at != expected_updated_at:
        raise EditorialConflict()
    return book


def record_metadata_version(book, user, edit_note=""):
    snapshot = {
        field: getattr(book, field)
        for field in ("title", "summary", *EDITORIAL_FIELDS, *BOOK_FORMAT_FIELDS)
    }
    MetadataVersion.objects.create(
        book=book,
        snapshot=snapshot,
        source="editorial",
        created_by=user,
        notes=edit_note,
    )


@transaction.atomic
def update_book_editorial(user, book_id, attributes):
    values = dict(attributes)
    book = revision_checked_book(user, book_id, values.pop("expected_updated_at"))
    record_metadata_version(book, user, values.pop("edit_note", ""))
    book.metadata_overrides = {**book.metadata_overrides, **values}
    for field, value in values.items():
        setattr(book, field, value)
    book.save()
    return book


@transaction.atomic
def withdraw_book(user, book_id, expected_updated_at):
    book = revision_checked_book(user, book_id, expected_updated_at)
    book.state = LifecycleState.ARCHIVED
    book.save(update_fields=["state", "updated_at"])
    return book

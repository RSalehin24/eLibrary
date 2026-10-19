from apps.accounts.models import User
from apps.catalog.discovery.management import metadata_managed_books
from apps.catalog.models import Book, MetadataReview, MetadataVersion
from apps.catalog.serializers.editorial import EDITORIAL_FIELDS
from apps.catalog.serializers.formats import BOOK_FORMAT_FIELDS
from apps.common.models import LifecycleState, ReviewState
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException

from .source_publication import source_publication_problem


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
    if snapshot["manual_price"] is not None:
        snapshot["manual_price"] = str(snapshot["manual_price"])
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
    for field, value in values.items():
        setattr(book, field, value)
    book.editorial_reviewed_at = None
    book.review_state = ReviewState.PENDING
    book.save()
    return book


@transaction.atomic
def review_book_editorial(user, book_id, expected_updated_at):
    book = revision_checked_book(user, book_id, expected_updated_at)
    reviewed_at = timezone.now()
    book.editorial_reviewed_at = reviewed_at
    book.metadata_last_reviewed_at = reviewed_at
    book.review_state = ReviewState.APPROVED
    MetadataReview.objects.create(
        book=book, state=ReviewState.APPROVED, requested_by=user, reviewer=user
    )
    book.save(
        update_fields=[
            "editorial_reviewed_at",
            "metadata_last_reviewed_at",
            "review_state",
            "updated_at",
        ]
    )
    return book


@transaction.atomic
def publish_book(user, book_id, expected_updated_at):
    book = revision_checked_book(user, book_id, expected_updated_at)
    problem = source_publication_problem(book)
    if problem:
        raise EditorialConflict(problem)
    book.state = LifecycleState.PUBLISHED
    book.review_state = ReviewState.APPROVED
    book.save(update_fields=["state", "review_state", "updated_at"])
    return book


@transaction.atomic
def withdraw_book(user, book_id, expected_updated_at):
    book = revision_checked_book(user, book_id, expected_updated_at)
    book.state = LifecycleState.ARCHIVED
    book.save(update_fields=["state", "updated_at"])
    return book

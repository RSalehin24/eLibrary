from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, PermissionDenied

from apps.access.models import PreviewAccessSession, ReadingSession
from apps.access.publication_models import PreparationState, PreparedPublication
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import Book, GeneratedAssetStatus, GeneratedAssetType
from apps.common.permissions import user_has_reader_access

from .document_safety import PREPARATION_VERSION
from .launch import launch_reader_session


class ReaderNotReady(APIException):
    status_code = 409
    default_code = "reader_not_ready"
    default_detail = "The EPUB is not ready for reading."


def authorized_reader_book(user, slug):
    book = catalog_object_by_slug(
        Book.objects.filter(deleted_at__isnull=True).only(
            "id", "title", "slug", "state", "deleted_at", "source_quality_state"
        ),
        slug,
    )
    if not user_has_reader_access(user, book):
        raise PermissionDenied("You do not have reader access for this book.")
    return book


def prepared_book_publication(book):
    asset = (
        book.generated_assets.filter(
            asset_type=GeneratedAssetType.EPUB,
            status=GeneratedAssetStatus.READY,
        )
        .only("checksum")
        .first()
    )
    if asset is None or not asset.checksum:
        raise ReaderNotReady()
    publication = PreparedPublication.objects.filter(
        checksum=asset.checksum,
        state=PreparationState.READY,
        manifest__preparation_version=PREPARATION_VERSION,
    ).first()
    if publication is None:
        raise ReaderNotReady()
    return publication


@transaction.atomic
def launch_prepared_reader(user, slug):
    book = authorized_reader_book(user, slug)
    publication = prepared_book_publication(book)
    return launch_publication_reader(user, book, publication)


@transaction.atomic
def launch_publication_reader(user, book, publication):
    session = launch_reader_session(user, book)
    if (
        session.prepared_publication_id
        and session.prepared_publication_id != publication.pk
    ):
        session = PreviewAccessSession.objects.create(
            user=user, book=book, launch_count=1
        )
    session.prepared_publication = publication
    session.save(update_fields=["prepared_publication", "updated_at"])
    state = reading_state(session)
    if not state.last_location:
        state.preview_session = session
    state.save(update_fields=["preview_session", "last_opened_at", "updated_at"])
    return session


def account_reader_session(user, identifier):
    session = get_object_or_404(
        PreviewAccessSession.objects.select_related(
            "book", "prepared_publication"
        ).only(
            "id",
            "user_id",
            "book_id",
            "expires_at",
            "prepared_publication_id",
            "book__id",
            "book__title",
            "book__slug",
            "book__source_quality_state",
            "book__state",
            "book__deleted_at",
            "prepared_publication__id",
            "prepared_publication__manifest",
            "prepared_publication__storage_reference",
        ),
        pk=identifier,
        user=user,
        book__deleted_at__isnull=True,
    )
    if not session.is_active:
        raise Http404("Reader session has expired.")
    if not user_has_reader_access(user, session.book):
        raise PermissionDenied("Reader access is no longer available.")
    publication = session.prepared_publication
    if (
        publication is None
        or publication.manifest.get("preparation_version") != PREPARATION_VERSION
    ):
        raise ReaderNotReady()
    return session


def reading_state(session):
    state, _ = ReadingSession.objects.select_related("preview_session").get_or_create(
        user_id=session.user_id,
        book_id=session.book_id,
        defaults={"preview_session": session},
    )
    return state


def progress_matches_edition(state, session):
    if not state.preview_session_id:
        # Imported locations predate prepared editions and retain structural validation.
        return True
    return (
        state.preview_session.prepared_publication_id == session.prepared_publication_id
    )

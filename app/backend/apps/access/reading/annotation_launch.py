from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.access.models import PreviewAccessSession
from apps.access.publication_models import PreparationState

from .annotations import personal_annotations
from .preparation import publication_files_available
from .sessions import (
    ReaderNotReady,
    authorized_reader_book,
    launch_publication_reader,
    prepared_book_publication,
)


@transaction.atomic
def launch_annotation_reader(user, model, identifier):
    annotation = get_object_or_404(
        personal_annotations(user, model).select_related("prepared_publication"),
        pk=identifier,
    )
    book = authorized_reader_book(user, annotation.book.slug)
    publication = annotation.prepared_publication or prepared_book_publication(book)
    if publication.state != PreparationState.READY or not publication_files_available(publication):
        raise ReaderNotReady()
    session = PreviewAccessSession.objects.filter(
        user=user, book=book, prepared_publication=publication,
        expires_at__gt=timezone.now(),
    ).first()
    return session or launch_publication_reader(user, book, publication)

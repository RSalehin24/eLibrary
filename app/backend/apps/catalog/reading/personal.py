from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.catalog.discovery.personal import visible_personal_books
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.editorial.service import EditorialConflict
from apps.catalog.models import PhysicalReadingLog, SavedBook


def personal_book(actor, slug):
    return catalog_object_by_slug(visible_personal_books(actor), slug)


@transaction.atomic
def set_saved_book(actor, slug, saved):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    book = personal_book(actor, slug)
    if saved:
        SavedBook.objects.get_or_create(user=actor, book=book)
    else:
        SavedBook.objects.filter(user=actor, book=book).delete()
    return saved


def physical_book(actor, slug):
    book = personal_book(actor, slug)
    if book.record_type != "manual":
        raise ValidationError({"book": "Reading logs apply to paper books."})
    return book


@transaction.atomic
def save_physical_log(actor, slug, values):
    values = dict(values)
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    book = physical_book(actor, slug)
    log = PhysicalReadingLog.objects.filter(user=actor, book=book).first()
    expected = values.pop("expected_updated_at")
    if (log is None and expected is not None) or (
        log is not None and log.updated_at != expected
    ):
        raise EditorialConflict("Your reading log changed. Refresh before saving.")
    if log is None:
        return PhysicalReadingLog.objects.create(user=actor, book=book, **values)
    for field, value in values.items():
        setattr(log, field, value)
    log.save()
    return log

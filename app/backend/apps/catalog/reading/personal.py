from django.db import transaction

from apps.accounts.models import User
from apps.catalog.discovery.personal import visible_personal_books
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import SavedBook


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

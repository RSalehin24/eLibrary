from django.db.models import Q

from apps.access.models import PermissionGrant
from apps.catalog.models import Book, ContributorRole
from apps.common.permissions import user_has_scope


def books_with_scopes(actor, scopes):
    books = Book.objects.filter(deleted_at__isnull=True)
    if not actor.is_active:
        return books.none()
    if user_has_scope(actor, scopes):
        return books
    grants = PermissionGrant.objects.active_for_user(actor).filter(scope__in=scopes)
    return books.filter(
        Q(pk__in=grants.values("book_id"))
        | Q(book_categories__category_id__in=grants.values("category_id"))
        | Q(
            book_contributors__contributor_id__in=grants.values("contributor_id"),
            book_contributors__role=ContributorRole.AUTHOR,
        )
    ).distinct()

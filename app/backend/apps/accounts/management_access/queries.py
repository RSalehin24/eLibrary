from django.db.models import Count, Exists, F, OuterRef, Q, QuerySet
from django.shortcuts import get_object_or_404
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.access.models import PermissionGrant
from apps.accounts.managed_user_queries import (
    apply_managed_user_search,
    ordered_managed_users_queryset,
)
from apps.accounts.models import User
from apps.catalog.models import Book, Category, Contributor, ContributorRole

from .policy import full_control_grants


def managed_accounts(parameters):
    queryset = User.objects.annotate(
        grant_count_value=Count("permission_grants", distinct=True),
        has_totp_enabled_value=Exists(
            TOTPDevice.objects.filter(user_id=OuterRef("pk"), confirmed=True)
        ),
        has_full_control_value=Exists(
            full_control_grants().filter(user_id=OuterRef("pk"))
        ),
    )
    queryset = apply_managed_user_search(queryset, parameters.get("q", ""))
    filters = {
        "active": {"is_active": True},
        "disabled": {"is_active": False},
        "setup_pending": {"email_setup_pending": True},
        "totp_required": {"totp_required": True},
    }
    return ordered_managed_users_queryset(
        queryset.filter(**filters.get(parameters.get("status"), {})),
        parameters.get("sort", "name_asc"),
    )


def managed_account(identifier):
    return get_object_or_404(managed_accounts({}), pk=identifier)


def account_grants(target):
    return (
        PermissionGrant.objects.filter(user=target)
        .select_related("user", "book", "category", "contributor")
        .order_by("-created_at", "-id")
    )


def access_references(parameters):
    kind, query = parameters["kind"], parameters["q"]
    if kind == "book":
        books = Book.objects.filter(deleted_at__isnull=True)
        return (
            books.filter(Q(title__icontains=query) | Q(catalog_code__icontains=query))
            .values("id", "slug", name=F("title"))
            .order_by("name", "id")
        )
    if kind == "author":
        authors = Contributor.objects.filter(
            book_contributions__role=ContributorRole.AUTHOR
        ).distinct()
        return named_references(authors, query)
    return named_references(Category.objects.all(), query)


def named_references(queryset: QuerySet[Contributor] | QuerySet[Category], query: str):
    return (
        queryset.filter(name__icontains=query)
        .values("id", "slug", "name")
        .order_by("name", "id")
    )

from django.db.models import Case, IntegerField, Q, Value, When
from django.db.models.functions import Lower
from django.utils import timezone

from apps.access.models import ACCOUNT_MANAGEABLE_PERMISSION_SCOPES


def apply_managed_user_search(queryset, raw_query):
    query = str(raw_query or "").strip().lower()
    if not query:
        return queryset

    search_filter = Q(email__icontains=query) | Q(full_name__icontains=query)

    if "active".find(query) != -1:
        search_filter |= Q(is_active=True)
    if "disabled".find(query) != -1:
        search_filter |= Q(is_active=False)
    if "required".find(query) != -1:
        search_filter |= Q(totp_required=True)
    if "enabled".find(query) != -1:
        search_filter |= Q(has_totp_enabled_value=True, totp_required=False)
    if "optional".find(query) != -1:
        search_filter |= Q(has_totp_enabled_value=False, totp_required=False)

    matching_scopes = [
        scope.value
        for scope in ACCOUNT_MANAGEABLE_PERMISSION_SCOPES
        if query in scope.value.lower() or query in scope.label.lower()
    ]
    if matching_scopes:
        search_filter |= (
            Q(permission_grants__expires_at__isnull=True)
            | Q(permission_grants__expires_at__gt=timezone.now())
        ) & Q(
            permission_grants__scope__in=matching_scopes,
            permission_grants__is_active=True,
            permission_grants__book__isnull=True,
            permission_grants__category__isnull=True,
            permission_grants__contributor__isnull=True,
        )

    return queryset.filter(search_filter).distinct()


def ordered_managed_users_queryset(queryset, sort_key):
    if sort_key == "name_desc":
        return queryset.order_by(Lower("full_name").desc(), Lower("email").desc(), "id")
    if sort_key == "email_asc":
        return queryset.order_by(Lower("email"), Lower("full_name"), "id")
    if sort_key == "email_desc":
        return queryset.order_by(Lower("email").desc(), Lower("full_name").desc(), "id")
    if sort_key == "status":
        return queryset.order_by(
            Case(
                When(is_active=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            Lower("full_name"),
            Lower("email"),
            "id",
        )
    return queryset.order_by(Lower("full_name"), Lower("email"), "id")

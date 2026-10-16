from apps.access.models import PermissionGrant, PermissionScope
from apps.catalog.models import Category, Contributor, CuratedCollection, Series
from apps.common.permissions import user_can_create_catalog_book
from django.db.models import Q
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

ENTITY_KINDS = ("contributors", "categories", "series", "collections")


def entity_model(kind):
    models = {
        "contributors": Contributor,
        "categories": Category,
        "series": Series,
        "collections": CuratedCollection,
    }
    if kind not in models:
        raise Http404
    return models[kind]


def manageable_entities(actor, kind):
    queryset = entity_model(kind).objects.all()
    if user_can_create_catalog_book(actor):
        return queryset
    if not actor.is_active or kind not in {"contributors", "categories"}:
        return queryset.none()
    grants = PermissionGrant.objects.active_for_user(actor).filter(
        scope=PermissionScope.METADATA_EDIT
    )
    field = "contributor_id" if kind == "contributors" else "category_id"
    return queryset.filter(pk__in=grants.values(field))


def require_entity_workspace(actor):
    from apps.accounts.workspaces import management_sections

    if "books" not in management_sections(actor):
        raise PermissionDenied("Metadata management access is required.")


def filtered_entities(actor, kind, query):
    from apps.common.text import normalize_catalog_text

    fields = ["id", "name", "slug", "updated_at", "editorial_reviewed_at"]
    if kind == "collections":
        fields.append("state")
    return (
        manageable_entities(actor, kind)
        .only(*fields)
        .filter(
            Q(normalized_name__contains=normalize_catalog_text(query))
            | Q(normalized_aliases__contains=normalize_catalog_text(query))
        )
        .order_by("name", "pk")
    )

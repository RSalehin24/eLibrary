from apps.catalog.discovery.management import metadata_managed_books
from apps.catalog.editorial.entity_policy import entity_model
from apps.common.text import normalize_catalog_text
from django.db.models import F, Q


def catalog_references(actor, parameters):
    kind, query = parameters["kind"], normalize_catalog_text(parameters["q"])
    if kind == "books":
        return (
            metadata_managed_books(actor)
            .filter(
                Q(normalized_title__contains=query)
                | Q(catalog_code=parameters["q"].upper())
            )
            .values("id", "catalog_code", name=F("title"))
            .order_by("name", "id")
        )
    return (
        entity_model(kind)
        .objects.filter(
            Q(normalized_name__contains=query) | Q(normalized_aliases__contains=query)
        )
        .values("id", "name", *(["catalog_code"] if kind != "collections" else []))
        .order_by("name", "id")
    )

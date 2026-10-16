from apps.catalog.views.managed_entities import (
    CatalogReferencesView,
    ManagedEntityDetailView,
    ManagedEntityListView,
)
from apps.catalog.views.relationships import BookRelationshipsView
from django.urls import path

catalog_entity_routes = [
    path(
        "manage/books/<str:slug>/relationships/",
        BookRelationshipsView.as_view(),
        name="managed-book-relationships",
    ),
    path(
        "manage/catalog-references/",
        CatalogReferencesView.as_view(),
        name="catalog-references",
    ),
    path(
        "manage/entities/<str:kind>/",
        ManagedEntityListView.as_view(),
        name="managed-entities",
    ),
    path(
        "manage/entities/<str:kind>/<uuid:identifier>/",
        ManagedEntityDetailView.as_view(),
        name="managed-entity-detail",
    ),
]

from apps.catalog.views.creation import ManagedBookCreationView
from apps.catalog.views.epub_uploads import ManagedEpubUploadView
from apps.catalog.views.exports import (
    CatalogExportView,
    LibraryExportView,
    ManagedBooksExportView,
    PhysicalBooksExportView,
    PhysicalBooksView,
)
from django.urls import path

catalog_creation_routes = [
    path("catalog/exports/", CatalogExportView.as_view(), name="catalog-exports"),
    path("me/books/export/", LibraryExportView.as_view(), name="my-book-export"),
    path(
        "manage/book-exports/",
        ManagedBooksExportView.as_view(),
        name="managed-book-export",
    ),
    path("catalog/physical-books/", PhysicalBooksView.as_view(), name="physical-books"),
    path(
        "catalog/physical-books/export/",
        PhysicalBooksExportView.as_view(),
        name="physical-book-export",
    ),
    path(
        "manage/books/<str:slug>/epub/",
        ManagedEpubUploadView.as_view(),
        name="managed-book-epub-upload",
    ),
    path(
        "manage/book-creations/<uuid:identifier>/",
        ManagedBookCreationView.as_view(),
        name="managed-book-creation",
    ),
]

from apps.catalog.views.creation import ManagedBookCreationView
from apps.catalog.views.epub_uploads import CreatedEpubUploadView, ManagedEpubUploadView
from apps.catalog.views.exports import (
    CatalogExportView,
    LibraryExportView,
    ManagedBooksExportView,
)
from django.urls import path

catalog_creation_routes = [
    path(
        "manage/book-creations/<uuid:identifier>/epub/",
        CreatedEpubUploadView.as_view(),
        name="created-book-epub-intake",
    ),
    path("catalog/exports/", CatalogExportView.as_view(), name="catalog-exports"),
    path("me/books/export/", LibraryExportView.as_view(), name="my-book-export"),
    path(
        "manage/book-exports/",
        ManagedBooksExportView.as_view(),
        name="managed-book-export",
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

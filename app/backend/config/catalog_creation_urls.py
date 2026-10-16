from apps.catalog.views.creation import ManagedBookCreationView
from apps.catalog.views.epub_uploads import ManagedEpubUploadView
from django.urls import path

catalog_creation_routes = [
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

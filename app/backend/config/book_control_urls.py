from apps.catalog.views.book_controls import (
    ManagedBookControlsView,
    RegenerateManagedBookView,
)
from django.urls import path

book_control_routes = [
    path(
        "manage/books/<str:slug>/controls/",
        ManagedBookControlsView.as_view(),
        name="managed-book-controls",
    ),
    path(
        "manage/books/<str:slug>/regenerate/",
        RegenerateManagedBookView.as_view(),
        name="managed-book-regenerate",
    ),
]

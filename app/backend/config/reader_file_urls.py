from apps.access.views.reader_html import ReaderHTMLView
from apps.catalog.views.covers import BookCoverView
from django.urls import path

reader_file_routes = [
    path("catalog/books/<str:slug>/cover/", BookCoverView.as_view(), name="book-cover"),
    path(
        "reading/books/<str:slug>/html/",
        ReaderHTMLView.as_view(),
        name="reader-html",
    ),
]

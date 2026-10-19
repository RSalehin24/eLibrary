from apps.access.views.detail_preview import BookDetailPreviewView
from apps.access.views.reader_html import ReaderHTMLView
from apps.catalog.views.covers import BookCoverView
from django.urls import path

reader_file_routes = [
    path(
        "reading/books/<str:slug>/details/",
        BookDetailPreviewView.as_view(),
        name="book-detail-preview",
    ),
    path("catalog/books/<str:slug>/cover/", BookCoverView.as_view(), name="book-cover"),
    path(
        "reading/books/<str:slug>/html/",
        ReaderHTMLView.as_view(),
        name="reader-html",
    ),
]

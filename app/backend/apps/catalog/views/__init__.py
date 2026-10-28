from apps.ingestion.services.submissions import queue_reprocess_book

from .assets import BookEpubReplaceView, BookRegenerateView
from .books import BookExportView, BookListView, BookMyBooksView, BookTicketExportView
from .details import BookDetailView, BookMetadataUpdateView, MetadataVersionListView
from .references import CategoryListView, ContributorListView, SeriesListView

__all__ = [
    "BookDetailView",
    "BookEpubReplaceView",
    "BookExportView",
    "BookListView",
    "BookMetadataUpdateView",
    "BookMyBooksView",
    "BookRegenerateView",
    "BookTicketExportView",
    "CategoryListView",
    "ContributorListView",
    "MetadataVersionListView",
    "SeriesListView",
    "queue_reprocess_book",
]

from apps.catalog.views.book_controls import RegenerateManagedBookView
from apps.catalog.views.epub_uploads import ManagedEpubUploadView


class BookEpubReplaceView(ManagedEpubUploadView):
    """The served legacy URL uses the same guarded preparation transaction."""


class BookRegenerateView(RegenerateManagedBookView):
    """Keep every served regeneration path on the versioned command policy."""

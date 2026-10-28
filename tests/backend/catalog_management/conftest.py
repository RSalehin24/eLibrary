import pytest
from apps.accounts.models import User
from apps.catalog.models import Book
from rest_framework.test import APIClient

from ..access.reader_fixtures import write_epub


@pytest.fixture
def upload_book(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.RUNTIME_STORAGE_DIR = tmp_path / "runtime"
    actor = User.objects.create_user(email="upload-admin@library.test", is_staff=True)
    book = Book.objects.create(title="আপলোডের বই", state="published")
    client = APIClient()
    client.force_authenticate(actor)
    return actor, book, client, write_epub(tmp_path / "book.epub")

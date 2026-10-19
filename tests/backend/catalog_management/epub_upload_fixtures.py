from django.core.files.uploadedfile import SimpleUploadedFile


def upload_url(book):
    return f"/api/v1/manage/books/{book.slug}/epub/"


def send_upload(fixture, **changes):
    _, book, client, path = fixture
    values = {
        "expected_updated_at": book.updated_at.isoformat(),
        "file": SimpleUploadedFile(
            "book.epub", path.read_bytes(), "application/epub+zip"
        ),
        **changes,
    }
    return client.post(upload_url(book), values, format="multipart")

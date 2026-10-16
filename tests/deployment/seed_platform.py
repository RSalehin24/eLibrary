import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import django
from seed_preview import create_account, create_books, create_collection
from seed_reader import create_reading_book, write_reader_fixture


def require_isolated_deployment():
    from django.conf import settings

    origin = urlsplit(settings.FRONTEND_BASE_URL)
    if (
        os.environ.get("ALLOW_DEPLOYMENT_FIXTURES") != "isolated-local-verification"
        or settings.APP_ENV != "production"
        or settings.DATABASES["default"]["HOST"] != "postgres"
        or origin.hostname != "library.example.test"
        or origin.port != 18443
    ):
        raise RuntimeError("Deployment fixtures require the isolated local test stack.")


def pending_asset():
    from apps.catalog.models import Book, GeneratedAsset
    from django.conf import settings

    book = Book.objects.create(title=f"কর্মীর পরীক্ষা {uuid4().hex[:8]}")
    path = Path(settings.MEDIA_ROOT) / "protected" / f"{book.pk}.epub"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_reader_fixture(path)
    return GeneratedAsset.objects.create(
        book=book, asset_type="epub", status="ready", legacy_path=str(path)
    )


def fixture_values():
    from django.db import transaction

    require_isolated_deployment()
    identity = uuid4().hex[:8]
    with transaction.atomic():
        owner, reader = create_account(identity, "reading-reader")
        _, administrator = create_account(identity, "administrator")
        reading_book = create_reading_book(owner)
        books = create_books(identity)
        collection = create_collection(identity, books)
        asset = pending_asset()
    return {
        "reading_reader": reader,
        "administrator": administrator,
        "reading_book": reading_book,
        "public_book": {"slug": books[0].slug, "title": books[0].title},
        "collection": collection,
        "pending_asset": {
            "id": str(asset.pk),
            "updated_at": asset.updated_at.isoformat(),
            "operation_id": str(uuid4()),
        },
    }


def main():
    os.umask(0o027)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    descriptor = os.open(
        os.environ["DEPLOYMENT_FIXTURE_PATH"],
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(fixture_values(), stream)


if __name__ == "__main__":
    main()

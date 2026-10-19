from apps.access.reading.preparation import publication_directory
from apps.ingestion.source_processing.classification import VALIDATOR_VERSION
from apps.ingestion.source_processing.content_text import canonical_text
from apps.ingestion.source_processing.documents import read_source_result
from apps.ingestion.source_processing.export_verification import verify_reading_text
from apps.processing.jobs.execution_errors import ExecutionFailure
from rest_framework.exceptions import ValidationError

from .service import EditorialConflict


def chapter_reading_text(path):
    data = path.read_bytes()
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    return canonical_text(data.decode(encoding))


def verify_uploaded_source_text(book, publication):
    if not book.source_urls.exists():
        return
    edition = book.source_editions.order_by("-created_at", "-pk").first()
    if (
        book.source_quality_state != "verified"
        or edition is None
        or edition.state != "published"
        or edition.validator_version != VALIDATOR_VERSION
        or not edition.validation_report.get("verified")
    ):
        raise EditorialConflict(
            "Regenerate the website book to verify its text before replacing the EPUB."
        )
    try:
        result = read_source_result(edition.operation_id, edition.document_reference)
    except ExecutionFailure:
        raise EditorialConflict(
            "The retained source evidence is unavailable. Regenerate the website book."
        ) from None
    directory = publication_directory(publication)
    text = " ".join(
        chapter_reading_text(directory / chapter["path"])
        for chapter in publication.manifest["chapters"]
    )
    if not verify_reading_text(result, text):
        raise ValidationError(
            {
                "file": "The EPUB reading text does not match every verified website chapter. "
                "Regenerate the book or upload its complete matching EPUB."
            }
        )

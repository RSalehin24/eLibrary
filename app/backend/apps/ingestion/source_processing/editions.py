from hashlib import sha256

from django.utils import timezone

from apps.ingestion.models import SourceEdition, SourceEditionPage
from apps.processing.job_models import BackgroundJob

from .classification import VALIDATOR_VERSION
from .storage import read_artifact


def edition_for_job(identifier):
    job = BackgroundJob.objects.only("source_record_id", "book_id").get(pk=identifier)
    if job.source_record_id is None:
        return None
    edition, _ = SourceEdition.objects.get_or_create(
        operation=job,
        defaults={"source_id": job.source_record_id, "book_id": job.book_id},
    )
    return edition


def record_source_page(identifier, page, reference):
    url, html = page
    edition = edition_for_job(identifier)
    if edition is None:
        return
    previous = (
        SourceEditionPage.objects.filter(edition=edition, url=url)
        .only("position")
        .first()
    )
    SourceEditionPage.objects.update_or_create(
        edition=edition,
        url=url,
        defaults={
            "content_hash": sha256(html.encode()).hexdigest(),
            "artifact_reference": reference,
            "fetched_at": timezone.now(),
            "position": previous.position if previous else edition.pages.count(),
        },
    )


def record_source_evidence(job, evidence, reference):
    edition = edition_for_job(job.pk)
    edition.book_id = job.book_id
    edition.validator_version = VALIDATOR_VERSION
    edition.classification = evidence["classification"]
    edition.document_reference = reference
    edition.validation_report = evidence
    edition.state = "validated" if evidence["verified"] else "quarantined"
    edition.save()
    return edition


def record_published_edition(job):
    edition = edition_for_job(job.pk)
    edition.book_id, edition.state = job.book_id, "published"
    edition.asset_manifest = {
        asset.asset_type: {"checksum": asset.checksum, "file": asset.file.name}
        for asset in job.book.generated_assets.filter(status="ready")
    }
    edition.save()


def backfill_cached_pages(identifier, pages):
    edition = edition_for_job(identifier)
    if edition is None:
        return
    known = set(edition.pages.values_list("url", flat=True))
    for url, reference in pages.items():
        if url not in known:
            record_source_page(
                identifier, (url, read_artifact(identifier, reference)), reference
            )

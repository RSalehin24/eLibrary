from hashlib import sha256
from uuid import uuid4


def processing_fixture(actor, label):
    from apps.ingestion.models import SourceCatalogEntry
    from apps.ingestion.pipeline.curated_pipeline import curate_scraped_book_data
    from apps.ingestion.source_processing.commands import request_source_processing
    from apps.ingestion.source_processing.storage import (
        source_job_directory,
        write_artifact,
    )
    from apps.ingestion.source_processing.summary import source_summary

    identity = uuid4().hex[:8]
    entry = SourceCatalogEntry.objects.create(
        source_url=f"https://source.example.test/books/workflow/{identity}/",
        title=f"{label} {identity}",
    )
    job = request_source_processing(actor, (uuid4(), entry.pk), entry.updated_at)
    payload = {
        "book_title": entry.title,
        "author": "পরীক্ষার লেখক",
        "main_content": "<h2>বাংলা পাঠ</h2><p>মূল বইয়ের বাংলা লেখা। সম্পূর্ণ পাঠের পরীক্ষার উৎস।</p>",
        "cover": "",
        "series": "",
        "book_type": "গল্প",
        "book_info": "",
        "dedication": "",
        "toc": [],
        "content_items": [],
        "output_folder": str(source_job_directory(job.pk)),
    }
    result = curate_scraped_book_data(entry.source_url, payload)
    job.checkpoint = {
        "document_ref": write_artifact(job.pk, result),
        "source_summary": source_summary(result),
    }
    job.save()
    return job, result


def create_source_processing_fixture(actor):
    from apps.catalog.models import Book
    from apps.ingestion.source_processing.persistence import persist_source_book
    from apps.processing.jobs.attempts import claim_attempt
    from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt

    duplicate, result = processing_fixture(actor, "একই নামে উৎস")
    candidate = Book.objects.create(
        title=result["projection"]["book_title"], summary="আগের সম্পাদকীয় পরিচিতি"
    )
    duplicate.state, duplicate.error_code = "needs_attention", "source_duplicate"
    duplicate.checkpoint = {
        **duplicate.checkpoint,
        "duplicate_book_ids": [str(candidate.pk)],
    }
    duplicate.save()
    failed, result = processing_fixture(actor, "অসম্পূর্ণ প্রস্তুতি")
    ownership = claim_attempt(failed.dispatches.get().pk)
    book = persist_source_book(ownership, result)
    fail_attempt(
        ownership, AttemptFailure(FailureKind.PERMANENT, "source_exports_missing")
    )
    failed.refresh_from_db()
    # This recovery fixture represents an export failure from before deployment.
    defect = failed.checkpoint["source_defect"]
    defect["code_version"] = "0" * 64
    defect["fingerprint"] = sha256(
        f"{defect['error_code']}:{defect['stage']}:{defect['code_version']}".encode()
    ).hexdigest()
    failed.save(update_fields=["checkpoint"])
    return {
        "duplicate": str(duplicate.pk),
        "candidate": str(candidate.pk),
        "candidate_title": candidate.title,
        "failed": str(failed.pk),
        "failed_source": str(failed.source_record_id),
        "draft": str(book.pk),
    }

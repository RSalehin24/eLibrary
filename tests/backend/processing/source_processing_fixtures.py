from contextlib import nullcontext
from uuid import uuid4

from apps.accounts.models import User
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.curated_pipeline import curate_scraped_book_data
from apps.ingestion.source_processing.commands import request_source_processing

SOURCE_URL = "https://source.test/books/new-book/"
TITLE = "নতুন উৎসের বই"


def create_source_job():
    actor = User.objects.create_user(
        email=f"source-processor-{uuid4().hex}@library.test", is_staff=True
    )
    entry = SourceCatalogEntry.objects.create(
        source_url=SOURCE_URL,
        title=TITLE,
        normalized_title=TITLE,
        normalized_display=TITLE,
    )
    return request_source_processing(actor, (uuid4(), entry.pk), entry.updated_at)


def source_payload(folder):
    return {
        "book_title": TITLE,
        "author": "পরীক্ষার লেখক",
        "series": "",
        "book_type": "গল্প",
        "cover": "",
        "main_content": "<h2>প্রথম অধ্যায়</h2><p>বইয়ের মূল বাংলা লেখা। পাঠকের জন্য পূর্ণ পাঠ।</p>",
        "book_info": "",
        "dedication": "",
        "toc": [],
        "content_items": [],
        "output_folder": str(folder),
    }


def curated_source(folder, source_url=SOURCE_URL):
    result = curate_scraped_book_data(source_url, source_payload(folder))
    result["source_snapshot"]["pages"] = [
        {"url": source_url, "status": "fetched", "status_code": 200}
    ]
    return result


def execute_source_job(job):
    from apps.processing.jobs.worker import run_background_job

    run_background_job(
        job.dispatches.get(generation=job.generation).pk, lambda _: nullcontext()
    )
    job.refresh_from_db()


def historical_duplicate(job, candidate):
    from apps.processing.jobs.attempts import checkpoint_attempt, claim_attempt
    from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt

    ownership = claim_attempt(job.dispatches.get(generation=job.generation).pk)
    checkpoint_attempt(
        ownership,
        {**job.checkpoint, "duplicate_book_ids": [str(candidate.pk)]},
        "source_duplicate",
    )
    fail_attempt(ownership, AttemptFailure(FailureKind.UNCERTAIN, "source_duplicate"))
    job.refresh_from_db()

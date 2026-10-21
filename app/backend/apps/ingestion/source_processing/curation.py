from apps.ingestion.pipeline.book_manifest import normalize_manifest_limits
from apps.ingestion.pipeline.manifest_collection import (
    CollectionOptions,
)

from .covers import download_source_cover
from .linked_books import SourceDocumentCollector
from .page_cache import ControlledSourceContext, SourcePageCache
from .policy import MAX_SOURCE_PAGES
from .storage import source_job_directory
from .transport import ControlledSourceSession


def curate_source_job(ownership, job):
    cache = SourcePageCache(ownership, job.checkpoint)
    folder = source_job_directory(job.pk) / str(ownership.attempt_id)
    limits = normalize_manifest_limits({"max_nodes": MAX_SOURCE_PAGES})
    options = CollectionOptions(
        limits, output_directory=folder, cover_downloader=download_source_cover
    )
    with ControlledSourceSession(cache.boundary) as session:
        context = ControlledSourceContext(session, cache)
        result = SourceDocumentCollector(context, options).collect(
            job.checkpoint.get("source_url", job.input["command"]["source_url"])
        )
    return result, cache.checkpoint

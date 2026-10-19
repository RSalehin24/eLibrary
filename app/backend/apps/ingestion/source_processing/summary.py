from .layout import source_layout
from .storage import artifact_path
from .verification import source_verification


def source_summary(result):
    projection = result.get("projection", {})
    validation = result.get("validation", {})
    return {
        "title": str(projection.get("book_title", ""))[:255],
        "author_line": str(projection.get("author", ""))[:255],
        "validation_status": result.get("status", ""),
        "error_count": len(validation.get("errors", [])),
        "warning_count": len(validation.get("warnings", [])),
        "verification": source_verification(result),
        "layout": source_layout(result.get("source_snapshot", {})),
    }


def source_document_available(job):
    reference = job.checkpoint.get("document_ref")
    if not reference:
        return False
    try:
        return artifact_path(job.pk, reference).is_file()
    except (OSError, ValueError):
        return False

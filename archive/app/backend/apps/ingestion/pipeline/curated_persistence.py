from django.db import IntegrityError, transaction
from django.db.models import Max

from apps.catalog.models import (
    Book,
    BookSource,
    CuratedBookDocument,
    CuratedDocumentStatus,
    CuratedEntity,
    CuratedEvidence,
    CuratedSection,
    MetadataVersion,
)
from apps.catalog.services import (
    find_deleted_book_by_title,
    find_existing_book_by_source_url,
    replace_book_relations,
)
from apps.ingestion.services.submissions_support.detection import find_existing_matching_book
from apps.common.models import LifecycleState, ReviewState
from apps.common.text import normalize_catalog_text
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.ingestion.services.normalization import (
    clean_extracted_dedication_html,
    normalize_scraped_book,
)

PROJECTION_HEAVY_KEYS = {
    "main_content",
    "book_info",
    "dedication",
    "front_sections",
    "back_sections",
    "content_items",
}


def _count_empty_toc_chapters(toc_nodes):
    """Recursively count non-section TOC nodes where has_content is not True."""
    count = 0
    for node in (toc_nodes or []):
        if node.get("type", "lesson") != "section":
            if node.get("has_content") is not True:
                count += 1
        count += _count_empty_toc_chapters(node.get("children", []))
    return count


def html_char_count(value):
    return len(value or "") if isinstance(value, str) else 0


def summarize_structured_sections(items):
    return [
        {
            "title": item.get("title", ""),
            "html_chars": html_char_count(item.get("html", "")),
        }
        for item in items or []
        if isinstance(item, dict)
    ]


def summarize_content_items(items):
    return [
        {
            "title": item.get("title", ""),
            "type": item.get("type", "lesson"),
            "parent": item.get("parent"),
            "path": item.get("path", []),
            "source_url": item.get("source_url", ""),
            "content_chars": html_char_count(item.get("content", "")),
        }
        for item in items or []
        if isinstance(item, dict)
    ]


def projection_content_summary(projection):
    content_items = projection.get("content_items") or []
    front_sections = projection.get("front_sections") or []
    back_sections = projection.get("back_sections") or []
    return {
        "main_content_chars": html_char_count(projection.get("main_content", "")),
        "book_info_chars": html_char_count(projection.get("book_info", "")),
        "dedication_chars": html_char_count(projection.get("dedication", "")),
        "front_section_count": len(front_sections),
        "front_sections": summarize_structured_sections(front_sections),
        "back_section_count": len(back_sections),
        "back_sections": summarize_structured_sections(back_sections),
        "content_item_count": len(content_items),
        "content_html_chars": sum(html_char_count(item.get("content", "")) for item in content_items if isinstance(item, dict)),
        "content_items": summarize_content_items(content_items),
    }


def slim_projection(projection):
    projection = projection or {}
    slimmed = {
        key: value
        for key, value in projection.items()
        if key not in PROJECTION_HEAVY_KEYS and key != "manifest"
    }
    slimmed["content_summary"] = projection_content_summary(projection)
    return slimmed


def slim_section_payload(section):
    slimmed = {key: value for key, value in (section or {}).items() if key != "html"}
    slimmed["html_chars"] = html_char_count((section or {}).get("html", ""))
    return slimmed


def slim_manifest(manifest):
    if not isinstance(manifest, dict):
        return {}
    slimmed = {
        key: value
        for key, value in manifest.items()
        if key not in {"projection", "sections"}
    }
    if "projection" in manifest:
        slimmed["projection"] = slim_projection(manifest.get("projection") or {})
    if "sections" in manifest:
        slimmed["sections"] = [slim_section_payload(section) for section in manifest.get("sections") or []]
    return slimmed


def slim_source_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return {}
    slimmed = {
        key: value
        for key, value in snapshot.items()
        if key not in {"raw_scrape_payload", "manifest"}
    }
    if "raw_scrape_payload" in snapshot:
        slimmed["raw_scrape_payload"] = slim_projection(snapshot.get("raw_scrape_payload") or {})
    if "manifest" in snapshot:
        slimmed["manifest"] = slim_manifest(snapshot.get("manifest") or {})
    return slimmed


def slim_document_payload(document):
    if not isinstance(document, dict):
        return {}
    slimmed = {
        key: value
        for key, value in document.items()
        if key not in {*PROJECTION_HEAVY_KEYS, "projection", "manifest", "sections"}
    }
    if "projection" in document:
        slimmed["projection"] = slim_projection(document.get("projection") or {})
    if "manifest" in document:
        slimmed["manifest"] = slim_manifest(document.get("manifest") or {})
    if "sections" in document:
        slimmed["sections"] = [slim_section_payload(section) for section in document.get("sections") or []]
    return slimmed


def next_document_version(source_url):
    current = (
        CuratedBookDocument.objects.filter(source_url=source_url)
        .aggregate(version=Max("version"))
        .get("version")
    )
    return int(current or 0) + 1


def persist_curated_document(curated_result, *, book=None, job=None):
    document_payload = curated_result["document"]
    source_url = document_payload.get("source_url") or document_payload.get("canonical_url", "")
    curated_document = None
    for _attempt in range(5):
        version = next_document_version(source_url)
        stored_document = {**slim_document_payload(document_payload), "model_version": version}
        try:
            with transaction.atomic():
                curated_document = CuratedBookDocument.objects.create(
                    book=book,
                    source_job=job,
                    source_url=source_url,
                    canonical_url=document_payload.get("canonical_url", ""),
                    version=version,
                    status=document_payload.get("status", CuratedDocumentStatus.DRAFT),
                    structure_type=document_payload.get("structure_type", ""),
                    title=document_payload.get("book", {}).get("clean_title", ""),
                    validation_summary=document_payload.get("validation", {}),
                    source_snapshot=slim_source_snapshot(curated_result.get("source_snapshot") or {}),
                    document=stored_document,
                )
            break
        except IntegrityError:
            # A concurrent or retried persist already claimed this version;
            # recompute the next version and try again.
            continue
    if curated_document is None:
        raise IntegrityError(
            f"Unable to allocate a curated document version for source_url={source_url!r}"
        )
    entity_map = {}
    for item in document_payload.get("entities", []):
        entity = CuratedEntity.objects.create(
            document=curated_document,
            entity_type=item.get("entity_type", ""),
            role=item.get("role", ""),
            value=item.get("value", ""),
            normalized_value=item.get("normalized_value") or normalize_catalog_text(item.get("value", "")),
            source_url=item.get("source_url", ""),
            source_location=item.get("source_location", ""),
            evidence_text=item.get("evidence_text", ""),
            confidence=item.get("confidence", 0),
            payload=item.get("payload", {}),
        )
        key = (entity.entity_type, entity.role, entity.normalized_value, entity.source_location)
        entity_map[key] = entity

    section_map = {}
    for item in document_payload.get("sections", []):
        section = CuratedSection.objects.create(
            document=curated_document,
            section_id=item.get("section_id", ""),
            section_type=item.get("section_type", ""),
            title=item.get("title", ""),
            path=item.get("path", []),
            source_url=item.get("source_url", ""),
            source_location=item.get("source_location", ""),
            html=item.get("html", ""),
            confidence=item.get("confidence", 0),
            sort_order=item.get("sort_order", 0),
            payload=item.get("payload", {}),
        )
        section_map[section.section_id] = section

    for item in document_payload.get("evidence", []):
        normalized = normalize_catalog_text(item.get("value", ""))
        entity_key = (item.get("entity_type", ""), item.get("role", ""), normalized, item.get("source_location", ""))
        CuratedEvidence.objects.create(
            document=curated_document,
            entity=entity_map.get(entity_key),
            section=section_map.get(item.get("section_id", "")),
            value=item.get("value", ""),
            entity_type=item.get("entity_type", ""),
            role=item.get("role", ""),
            source_url=item.get("source_url", ""),
            source_location=item.get("source_location", ""),
            evidence_text=item.get("evidence_text", ""),
            confidence=item.get("confidence", 0),
            extractor=item.get("extractor", ""),
            payload=item.get("payload", {}),
        )
    return curated_document


def persist_curated_book(curated_result, *, source_url, job=None, target_book=None):
    return persist_curated_book_with_hooks(
        curated_result,
        source_url=source_url,
        job=job,
        target_book=target_book,
    )


def persist_curated_book_with_hooks(
    curated_result,
    *,
    source_url,
    job=None,
    target_book=None,
    find_deleted_book_by_title_fn=find_deleted_book_by_title,
    find_existing_book_by_source_url_fn=find_existing_book_by_source_url,
    find_existing_matching_book_fn=find_existing_matching_book,
    replace_book_relations_fn=replace_book_relations,
):
    projection = curated_result["projection"]
    document_payload = curated_result.get("document") or {}
    manifest = document_payload.get("manifest") or {}
    normalized_url = normalize_source_url(source_url)
    normalization_payload = {
        **projection,
        "series": ", ".join(projection.get("series", []))
        if isinstance(projection.get("series"), list)
        else projection.get("series", ""),
        "book_type": ", ".join(projection.get("book_type", []))
        if isinstance(projection.get("book_type"), list)
        else projection.get("book_type", ""),
    }
    normalized = normalize_scraped_book(normalization_payload)
    cleaned_dedication_html = clean_extracted_dedication_html(projection.get("dedication", ""))
    raw_scraped_metadata = {
        **normalized["raw_strings"],
        "source_url": normalized_url,
        "curated_document_status": document_payload.get("status", ""),
    }
    lifecycle_state = LifecycleState.READY
    review_state = ReviewState.PENDING
    if document_payload.get("status") != CuratedDocumentStatus.VALIDATED:
        lifecycle_state = LifecycleState.NEEDS_REVIEW
        review_state = ReviewState.NEEDS_REVIEW

    def apply_fields(book):
        book.deleted_at = None
        book.state = lifecycle_state
        book.review_state = review_state
        book.raw_scraped_metadata = raw_scraped_metadata
        book.raw_scrape_payload = {
            **slim_projection(projection),
            "manifest": slim_manifest(manifest),
            "curated_document_version": document_payload.get("schema_version", ""),
            "curated_document_status": document_payload.get("status", ""),
            "curated_validation": document_payload.get("validation", {}),
        }
        book.main_content_html = projection.get("main_content", "")
        book.book_info_html = projection.get("book_info", "")
        book.dedication_html = cleaned_dedication_html
        book.toc = projection.get("toc", [])
        book.content_items = projection.get("content_items", [])
        book.empty_chapters_count = _count_empty_toc_chapters(book.toc)
        book.cover_source_url = (
            projection.get("cover_source_url")
            or (manifest.get("projection") or {}).get("cover_source_url")
            or projection.get("cover")
            or ""
        )

    existing_book = (
        target_book
        or find_deleted_book_by_title_fn(projection["book_title"])
        or find_existing_matching_book_fn(projection["book_title"], normalized)
    )
    if existing_book:
        book = existing_book
        apply_fields(book)
        book.save(update_fields=["deleted_at", "state", "review_state", "raw_scraped_metadata", "raw_scrape_payload", "main_content_html", "book_info_html", "dedication_html", "toc", "content_items", "empty_chapters_count", "cover_source_url", "updated_at"])
    else:
        create_kwargs = {
            "title": projection["book_title"],
            "state": lifecycle_state,
            "review_state": review_state,
        }
        book = Book(**create_kwargs)
        apply_fields(book)
        create_kwargs = {
            "title": book.title,
            "state": book.state,
            "review_state": book.review_state,
            "raw_scraped_metadata": book.raw_scraped_metadata,
            "raw_scrape_payload": book.raw_scrape_payload,
            "main_content_html": book.main_content_html,
            "book_info_html": book.book_info_html,
            "dedication_html": book.dedication_html,
            "toc": book.toc,
            "content_items": book.content_items,
            "empty_chapters_count": book.empty_chapters_count,
            "cover_source_url": book.cover_source_url,
        }
        try:
            with transaction.atomic():
                book = Book.objects.create(**create_kwargs)
        except IntegrityError:
            book = (
                find_existing_book_by_source_url_fn(normalized_url)
                or find_existing_matching_book_fn(projection["book_title"], normalized)
            )
            if book is None:
                raise
            apply_fields(book)
            book.save(update_fields=["deleted_at", "state", "review_state", "raw_scraped_metadata", "raw_scrape_payload", "main_content_html", "book_info_html", "dedication_html", "toc", "content_items", "empty_chapters_count", "cover_source_url", "updated_at"])

    replace_book_relations_fn(
        book,
        contributors=normalized["contributors"],
        series_names=normalized["series"],
        category_names=normalized["categories"],
    )
    BookSource.objects.update_or_create(
        normalized_source_url=normalized_url,
        defaults={
            "book": book,
            "source_url": normalized_url,
            "source_title": projection.get("book_title", ""),
            "raw_metadata": raw_scraped_metadata,
        },
    )
    curated_document = persist_curated_document(curated_result, book=book, job=job)
    book.raw_scrape_payload = {
        **book.raw_scrape_payload,
        "curated_document_model_id": str(curated_document.id),
        "curated_document_model_version": curated_document.version,
    }
    book.save(update_fields=["raw_scrape_payload", "updated_at"])

    # Phase E: honour BookGroup linkage hint stashed on the submission's
    # raw_payload by the "new_edition" duplicate-resolution action. Both
    # the freshly-created book and the existing duplicate book are linked
    # to the same BookGroup so the catalog can surface them as siblings.
    submission = getattr(job, "submission", None)
    group_hint = None
    if submission is not None:
        group_hint = (submission.raw_payload or {}).get("target_book_group_id")
    if group_hint and not book.group_id:
        from apps.catalog.models import BookGroup as _BookGroup
        try:
            group = _BookGroup.objects.filter(pk=group_hint).first()
        except (ValueError, TypeError):
            group = None
        if group is not None:
            book.group = group
            book.save(update_fields=["group", "updated_at"])
    MetadataVersion.objects.create(book=book, snapshot=curated_document.document, source="curated")
    return book, curated_document

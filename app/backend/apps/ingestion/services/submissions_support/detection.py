from apps.catalog.models import Book, BookGroup, ContributorRole
from apps.common.text import normalize_catalog_text
from apps.ingestion.services.resolution_support_hosts import get_source_site_domain


def normalized_role_names(normalized_scraped, role):
    return {
        normalize_catalog_text(entry["name"])
        for entry in normalized_scraped.get("contributors", [])
        if entry.get("role") == role and normalize_catalog_text(entry.get("name", ""))
    }


def normalized_value_set(values):
    return {normalize_catalog_text(value) for value in values if normalize_catalog_text(value)}


def related_role_names(book, role):
    return {
        normalize_catalog_text(relation.contributor.name)
        for relation in book.book_contributors.all()
        if relation.role == role and normalize_catalog_text(relation.contributor.name)
    }


def related_category_names(book):
    return {
        normalize_catalog_text(relation.category.name)
        for relation in book.book_categories.all()
        if normalize_catalog_text(relation.category.name)
    }


def related_series_names(book):
    return {
        normalize_catalog_text(relation.series.name)
        for relation in book.book_series.all()
        if normalize_catalog_text(relation.series.name)
    }


def detect_metadata_duplicate(scraped_data, *, normalize_scraped_book_fn, texts_are_similar_fn):
    target_title = scraped_data.get("book_title", "")
    normalized_scraped = normalize_scraped_book_fn(scraped_data)
    target_author_names = normalized_role_names(normalized_scraped, ContributorRole.AUTHOR)
    target_translator_names = normalized_role_names(normalized_scraped, ContributorRole.TRANSLATOR)
    target_category_names = normalized_value_set(normalized_scraped.get("categories", []))
    target_series_names = normalized_value_set(normalized_scraped.get("series", []))

    if not target_title:
        return None

    books = Book.objects.filter(deleted_at__isnull=True).prefetch_related(
        "book_contributors__contributor",
        "book_categories__category",
        "book_series__series",
    )
    for book in books:
        if not texts_are_similar_fn(target_title, book.title):
            continue

        existing_author_names = related_role_names(book, ContributorRole.AUTHOR)
        existing_translator_names = related_role_names(book, ContributorRole.TRANSLATOR)
        existing_category_names = related_category_names(book)
        existing_series_names = related_series_names(book)

        if not target_author_names or not existing_author_names:
            continue
        if not target_category_names or not existing_category_names:
            continue
        if not (target_category_names & existing_category_names):
            continue
        if target_series_names and not (target_series_names & existing_series_names):
            continue
        if target_translator_names and not (target_translator_names & existing_translator_names):
            continue
        if target_author_names & existing_author_names:
            return book

    return None


def find_exact_existing_book(scraped_data, *, normalize_scraped_book_fn):
    normalized_title = normalize_catalog_text(scraped_data.get("book_title", ""))
    if not normalized_title:
        return None

    source_site = get_source_site_domain()
    candidate_books = (
        Book.objects.filter(
            source_site=source_site,
            normalized_title=normalized_title,
            deleted_at__isnull=True,
        )
        .prefetch_related(
            "book_contributors__contributor",
            "book_categories__category",
            "book_series__series",
        )
        .order_by("-created_at")
    )

    normalized_scraped = normalize_scraped_book_fn(scraped_data)
    target_author_names = normalized_role_names(normalized_scraped, ContributorRole.AUTHOR)
    target_translator_names = normalized_role_names(normalized_scraped, ContributorRole.TRANSLATOR)
    target_category_names = normalized_value_set(normalized_scraped.get("categories", []))
    target_series_names = normalized_value_set(normalized_scraped.get("series", []))

    if not target_author_names or not target_category_names:
        return None

    for book in candidate_books:
        existing_author_names = related_role_names(book, ContributorRole.AUTHOR)
        existing_translator_names = related_role_names(book, ContributorRole.TRANSLATOR)
        existing_category_names = related_category_names(book)
        existing_series_names = related_series_names(book)

        if not existing_author_names or not existing_category_names:
            continue
        if not (target_category_names & existing_category_names):
            continue
        if target_series_names and not (target_series_names & existing_series_names):
            continue
        if target_translator_names and not (target_translator_names & existing_translator_names):
            continue
        if target_author_names & existing_author_names:
            return book

    return None


def find_existing_matching_book(book_title, normalized_scraped):
    """Return a live (non-deleted) Book that represents the same work.

    Matching rules:
    - Must share the same normalised title and source site.
    - Must share at least one author name.  If the incoming data has no
      author information the match is skipped (safer to create a new record
      than to accidentally merge unrelated books).
    - If *both* the incoming data *and* the candidate have translator names,
      they must share at least one translator; otherwise they are treated as
      different editions and the candidate is skipped.

    Returns the first matching Book, or None if no safe match is found.
    """
    normalized_title = normalize_catalog_text(book_title or "")
    if not normalized_title:
        return None

    target_author_names = normalized_role_names(normalized_scraped, ContributorRole.AUTHOR)
    if not target_author_names:
        # Cannot determine authorship — refuse to merge to avoid false positives.
        return None

    target_translator_names = normalized_role_names(normalized_scraped, ContributorRole.TRANSLATOR)

    source_site = get_source_site_domain()
    candidates = (
        Book.objects.filter(
            source_site=source_site,
            normalized_title=normalized_title,
            deleted_at__isnull=True,
        )
        .prefetch_related("book_contributors__contributor")
        .order_by("-created_at")
    )

    for book in candidates:
        existing_author_names = related_role_names(book, ContributorRole.AUTHOR)
        existing_translator_names = related_role_names(book, ContributorRole.TRANSLATOR)

        # Different author → different book entirely.
        if existing_author_names and not (target_author_names & existing_author_names):
            continue

        # Existing book has no recorded authors but the incoming submission
        # does. Refuse to silently merge — we cannot confirm the works match
        # without overlapping authorship data on both sides. The caller will
        # treat this as a duplicate-title conflict and surface it for review
        # / retry instead of overwriting the existing record.
        if target_author_names and not existing_author_names:
            continue

        # Both sides have translator info but no overlap → different edition.
        if target_translator_names and existing_translator_names:
            if not (target_translator_names & existing_translator_names):
                continue

        return book

    return None


# ---------------------------------------------------------------------------
# Phase D: classify incoming book against existing catalog
# ---------------------------------------------------------------------------

CLASSIFY_EXACT_DUPLICATE = "exact_duplicate"
CLASSIFY_NEW_EDITION = "new_edition"
CLASSIFY_NEW_WORK = "new_work"
CLASSIFY_NEEDS_REVIEW = "needs_review"


def _publisher_value(book):
    return normalize_catalog_text(getattr(book, "manual_publisher", "") or "")


def _edition_value(book):
    return normalize_catalog_text(getattr(book, "normalized_edition", "") or getattr(book, "edition", "") or "")


def classify_incoming_book(scraped_data, *, normalize_scraped_book_fn):
    """Classify an incoming scraped book against the existing catalog.

    Returns a dict::

        {
            "verdict": one of CLASSIFY_*,
            "matched_book": Book | None,
            "suggested_group": BookGroup | None,
            "reason": str,
        }

    Classification matrix:
      - No title-matching candidate found  → NEW_WORK.
      - Title matches but authors differ on both sides → NEW_WORK.
      - All of (author, translator, publisher, edition) overlap or are
        both empty → EXACT_DUPLICATE.
      - Title + author overlap but translator / publisher / edition differ
        on both sides → NEW_EDITION (with suggested_group pointing at the
        existing book's BookGroup, creating one lazily).
      - Title matches but the existing record has no author info while the
        incoming one does (or vice-versa) → NEEDS_REVIEW.
    """
    normalized_scraped = normalize_scraped_book_fn(scraped_data)
    book_title = scraped_data.get("book_title", "")
    normalized_title = normalize_catalog_text(book_title)
    if not normalized_title:
        return {
            "verdict": CLASSIFY_NEW_WORK,
            "matched_book": None,
            "suggested_group": None,
            "reason": "no_title",
        }

    target_authors = normalized_role_names(normalized_scraped, ContributorRole.AUTHOR)
    target_translators = normalized_role_names(normalized_scraped, ContributorRole.TRANSLATOR)
    target_publisher = normalize_catalog_text(
        (normalized_scraped.get("raw_strings") or {}).get("manual_publisher")
        or scraped_data.get("publisher", "")
        or scraped_data.get("manual_publisher", "")
    )
    target_edition = normalize_catalog_text(
        scraped_data.get("edition", "")
        or (normalized_scraped.get("raw_strings") or {}).get("edition", "")
    )

    source_site = get_source_site_domain()
    candidates = list(
        Book.objects.filter(
            source_site=source_site,
            normalized_title=normalized_title,
            deleted_at__isnull=True,
        ).prefetch_related("book_contributors__contributor", "group")
    )
    if not candidates:
        return {
            "verdict": CLASSIFY_NEW_WORK,
            "matched_book": None,
            "suggested_group": None,
            "reason": "no_title_match",
        }

    needs_review_candidate = None

    for book in candidates:
        existing_authors = related_role_names(book, ContributorRole.AUTHOR)
        existing_translators = related_role_names(book, ContributorRole.TRANSLATOR)
        existing_publisher = _publisher_value(book)
        existing_edition = _edition_value(book)

        # Author asymmetry: one side has info, the other does not.
        if bool(target_authors) ^ bool(existing_authors):
            needs_review_candidate = book
            continue

        # Both sides have authors but no overlap → different work.
        if target_authors and existing_authors and not (target_authors & existing_authors):
            continue

        # At this point either both sides are author-empty or they share
        # at least one author. Check the differentiating fields.
        translator_differs = bool(target_translators and existing_translators) and not (
            target_translators & existing_translators
        )
        publisher_differs = bool(target_publisher and existing_publisher) and (
            target_publisher != existing_publisher
        )
        edition_differs = bool(target_edition and existing_edition) and (
            target_edition != existing_edition
        )

        if translator_differs or publisher_differs or edition_differs:
            suggested_group = book.group or BookGroup.objects.filter(
                normalized_canonical_title=normalized_title
            ).first()
            return {
                "verdict": CLASSIFY_NEW_EDITION,
                "matched_book": book,
                "suggested_group": suggested_group,
                "reason": "different_edition",
            }

        return {
            "verdict": CLASSIFY_EXACT_DUPLICATE,
            "matched_book": book,
            "suggested_group": book.group,
            "reason": "all_fields_overlap",
        }

    if needs_review_candidate is not None:
        return {
            "verdict": CLASSIFY_NEEDS_REVIEW,
            "matched_book": needs_review_candidate,
            "suggested_group": needs_review_candidate.group,
            "reason": "author_metadata_asymmetric",
        }

    return {
        "verdict": CLASSIFY_NEW_WORK,
        "matched_book": None,
        "suggested_group": None,
        "reason": "no_author_overlap",
    }

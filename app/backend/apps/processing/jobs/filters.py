import re
from uuid import UUID

from django.db.models import Q

from apps.ingestion.source_processing.layout import (
    INLINE_SOURCE_LAYOUTS,
    NESTED_SOURCE_LAYOUTS,
)

VIEW_STATES = {
    "active": ("queued", "running", "retry_wait", "paused"),
    "history": ("succeeded", "failed", "cancelled"),
    "recovery": ("retry_wait", "paused", "failed", "needs_attention"),
}
EXACT_FILTERS = {"state", "kind", "book", "automation_run", "parent_job", "error_code"}


def search_jobs(queryset, query):
    if not query:
        return queryset
    matches = (
        Q(book__title__icontains=query)
        | Q(source_record__title__icontains=query)
        | Q(error_code__icontains=query)
    )
    try:
        matches |= Q(pk=UUID(query))
    except ValueError:
        pass
    if re.fullmatch(r"[0-9a-f]{12,64}", query):
        matches |= Q(checkpoint__source_defect__fingerprint__startswith=query)
    return queryset.filter(matches)


def filter_job_coverage(queryset, coverage):
    if not coverage:
        return queryset
    queryset = queryset.filter(kind="process_source")
    if coverage == "unverified":
        return queryset.filter(
            Q(checkpoint__source_summary__verification__verified__isnull=True)
            | Q(checkpoint__source_summary__verification__verified=None)
        )
    return queryset.filter(
        checkpoint__source_summary__verification__verified=coverage == "verified"
    )


def filter_job_layout(queryset, layout):
    if not layout:
        return queryset
    queryset = queryset.filter(kind="process_source")
    multi_page = Q(checkpoint__source_summary__layout__multi_page=True)
    nested = Q(
        checkpoint__source_summary__layout__structure_type__in=NESTED_SOURCE_LAYOUTS
    )
    matches = {
        "multi_page": multi_page,
        "nested": nested,
        "complex": multi_page | nested,
        "inline": Q(
            checkpoint__source_summary__layout__structure_type__in=INLINE_SOURCE_LAYOUTS
        ),
        "unclassified": Q(checkpoint__source_summary__layout__isnull=True)
        | Q(checkpoint__source_summary__layout=None),
    }
    return queryset.filter(matches[layout])


def filtered_jobs(queryset, parameters):
    queryset = queryset.filter(
        **{key: value for key, value in parameters.items() if key in EXACT_FILTERS}
    )
    if view := parameters.get("view"):
        queryset = queryset.filter(state__in=VIEW_STATES[view])
    queryset = filter_job_coverage(queryset, parameters.get("coverage"))
    queryset = filter_job_layout(queryset, parameters.get("layout"))
    return search_jobs(queryset, parameters.get("q", ""))

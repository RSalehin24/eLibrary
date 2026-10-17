from django.db.models import Q

from apps.processing.models import BookRecord
from apps.processing.service_modules.catalog_phase_helpers import (
    incomplete_category_query,
)


def unfinished_source_query():
    legacy = BookRecord.objects.filter(resolved_from_incomplete=False).filter(
        Q(was_incomplete=True) | incomplete_category_query()
    )
    stored = Q(raw_data__source_unfinished=True)
    unclassified = Q(raw_data__source_unfinished__isnull=True)
    metadata = (
        Q(raw_data__incompleteCategoryUrl__isnull=False)
        | Q(raw_data__category__icontains="অসম্পূর্ণ")
        | Q(pk__in=legacy.values("source_catalog_entry_id"))
    )
    return stored | (unclassified & metadata)

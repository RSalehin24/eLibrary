from apps.catalog.discovery.sorting import (
    CatalogSortPagination,
)


def ordered_export_queryset(queryset, parameters):
    if not parameters.get("sort"):
        return queryset.order_by("search_rank", "-created_at", "-id")
    ordering = CatalogSortPagination(parameters["sort"])
    prefix = "-" if ordering.descending else ""
    return ordering.prepared_queryset(queryset).order_by(
        prefix + "catalog_sort_value", prefix + "id"
    )

import hashlib
import json

from apps.common.ranked_pagination import RANKED_ORDERING, ranked_page
from apps.common.text import normalize_catalog_text

from .sorting import CatalogSortPagination

DISCOVERY_ORDERING = RANKED_ORDERING


def cursor_context(parameters):
    filters = {
        name: parameters.get(name, "")
        for name in (
            "category",
            "contributor",
            "contributor_role",
            "series",
            "collection",
            "ownership",
            "sort",
        )
    }
    filters["q"] = normalize_catalog_text(parameters["q"])
    filters["identifier"] = parameters["q"].upper()
    filters["ordering"] = DISCOVERY_ORDERING
    filters["scope"] = parameters.get("scope", "public")
    return hashlib.sha256(json.dumps(filters, sort_keys=True).encode()).hexdigest()


def discovery_page(queryset, parameters):
    if parameters.get("sort"):
        return CatalogSortPagination(parameters["sort"]).page(
            queryset, parameters, cursor_context(parameters)
        )
    return ranked_page(queryset, parameters, cursor_context(parameters))

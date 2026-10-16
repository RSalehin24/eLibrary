from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response


def bounded_positive_int(raw_value, *, default, minimum=1, maximum=100):
    try:
        value = int(str(raw_value).strip() or default)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


class OptionalPaginationListMixin(ListModelMixin, GenericAPIView):
    pagination_default_limit = 60
    pagination_max_limit = 100

    def list(self, request, *args, **kwargs):
        if "page" not in request.query_params and "limit" not in request.query_params:
            return super().list(request, *args, **kwargs)

        queryset = self.filter_queryset(self.get_queryset())
        limit_value = bounded_positive_int(
            request.query_params.get("limit"),
            default=self.pagination_default_limit,
            maximum=self.pagination_max_limit,
        )
        page_value = bounded_positive_int(
            request.query_params.get("page"),
            default=1,
            maximum=10_000,
        )
        total_count = queryset.count()
        page_count = max(1, ((total_count - 1) // limit_value) + 1) if total_count else 1
        page_value = min(page_value, page_count)
        start = (page_value - 1) * limit_value
        page_entries = queryset[start : start + limit_value]
        serializer = self.get_serializer(page_entries, many=True)
        return Response(
            {
                "entries": serializer.data,
                "pagination": {
                    "page": page_value,
                    "limit": limit_value,
                    "total_count": total_count,
                    "page_count": page_count,
                    "has_previous": page_value > 1,
                    "has_next": page_value < page_count,
                },
            }
        )


from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class BoundedAdminPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "limit"
    max_page_size = 100

    def get_paginated_response(self, data):
        if self.page is None or self.request is None:
            raise RuntimeError("Paginate the queryset before building its response.")
        return Response(
            {
                "entries": data,
                "pagination": {
                    "page": self.page.number,
                    "limit": self.get_page_size(self.request),
                    "total_count": self.page.paginator.count,
                },
            }
        )

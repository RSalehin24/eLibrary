from uuid import uuid4

from apps.catalog.models import Book


def create_pagination_fixture():
    query = f"pagination-{uuid4().hex}"
    for index in range(240):
        Book.objects.create(title=f"{query} {index:03}", state="published")
    return {"query": query, "total_count": 240, "page_count": 10}

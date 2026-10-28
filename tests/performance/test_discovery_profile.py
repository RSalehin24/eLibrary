import json
import statistics
import time
from pathlib import Path

import pytest
from apps.catalog.discovery.queries import discovery_queryset
from apps.catalog.models import Book, BookContributor, Contributor
from apps.catalog.models.catalog_codes import catalog_code_from_int
from apps.common.text import normalize_catalog_text
from django.db import connection
from django.test.utils import CaptureQueriesContext

CATALOG_SIZE = 10_000
SAMPLE_COUNT = 20
pytestmark = pytest.mark.django_db


def seed_profile_corpus():
    author = Contributor.objects.create(name="পরীক্ষার লেখক")
    books = Book.objects.bulk_create(
        [
            Book(
                title=f"পরীক্ষার উপন্যাস {index}",
                normalized_title=normalize_catalog_text(f"পরীক্ষার উপন্যাস {index}"),
                slug=f"profile-book-{index}",
                catalog_code=catalog_code_from_int(index),
                state="published",
            )
            for index in range(CATALOG_SIZE)
        ]
    )
    BookContributor.objects.bulk_create(
        [
            BookContributor(book=book, contributor=author, role="author")
            for book in books
        ]
    )
    with connection.cursor() as cursor:
        for model in (Book, BookContributor, Contributor):
            cursor.execute("ANALYZE " + connection.ops.quote_name(model._meta.db_table))


def measured_request(client, query):
    started = time.perf_counter()
    with CaptureQueriesContext(connection) as statements:
        response = client.get("/api/v1/catalog/books/", {"q": query})
    elapsed = (time.perf_counter() - started) * 1000
    assert response.status_code == 200
    assert response.json()["entries"]
    assert len(statements) == 4
    return elapsed


def explain_query(query):
    parameters = {
        "q": query,
        "category": "",
        "contributor": "",
        "series": "",
        "collection": "",
    }
    queryset = discovery_queryset(parameters).order_by(
        "search_rank", "-created_at", "-id"
    )[:24]
    statement, values = queryset.query.sql_with_params()
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, values)
        plan = cursor.fetchone()[0][0]
    return {
        "planning_ms": plan["Planning Time"],
        "execution_ms": plan["Execution Time"],
        "plan": plan["Plan"],
    }


def test_representative_postgresql_discovery_profile(client):
    seed_profile_corpus()
    measurements = []
    for query in ["পরীক্ষার উপন্যাস 27", "উপন্যাস পরীক্ষার লেখক", "পরীক্ষার লেখক"]:
        samples = [measured_request(client, query) for _ in range(SAMPLE_COUNT)]
        measurements.append(
            {
                "query": query,
                "samples": SAMPLE_COUNT,
                "queries_per_request": 4,
                "median_ms": statistics.median(samples),
                "p95_ms": sorted(samples)[18],
                **explain_query(query),
            }
        )
    report = {
        "scope": "synthetic local PostgreSQL test database",
        "catalog_size": CATALOG_SIZE,
        "measurements": measurements,
    }
    destination = (
        Path(__file__).resolve().parents[2]
        / "test-artifacts/performance/discovery-profile.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

from unittest.mock import Mock

import pytest
from django.db import DatabaseError, connection


def test_liveness_needs_no_database_or_credentials(client, monkeypatch):
    cursor = Mock(side_effect=DatabaseError("synthetic unavailable database"))
    monkeypatch.setattr(connection, "cursor", cursor)
    response = client.get("/api/v1/health/live/")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Robots-Tag"] == "noindex" and cursor.call_count == 0


@pytest.mark.django_db
def test_readiness_checks_the_database_without_revealing_configuration(client):
    response = client.get("/api/v1/health/ready/")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


def test_unavailable_database_has_a_bounded_readiness_error(client, monkeypatch):
    monkeypatch.setattr(
        connection,
        "cursor",
        Mock(side_effect=DatabaseError("synthetic database credentials")),
    )
    response = client.get("/api/v1/health/ready/")
    assert (
        response.status_code == 503 and response.json()["code"] == "service_unavailable"
    )
    assert response.json()["field_errors"] == {}
    assert "synthetic" not in response.content.decode()

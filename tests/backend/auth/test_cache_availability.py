from unittest.mock import Mock

import pytest
from apps.common.throttles import LoginRateThrottle, PasswordLinkRateThrottle
from redis.exceptions import ConnectionError

pytestmark = pytest.mark.django_db


def unavailable_cache():
    return Mock(get=Mock(side_effect=ConnectionError("synthetic cache outage")))


def test_login_denies_a_cache_outage_without_exposing_service_details(
    client, monkeypatch
):
    monkeypatch.setattr(LoginRateThrottle, "cache", unavailable_cache())
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "reader@example.test", "password": "synthetic-test-password"},
        content_type="application/json",
    )
    assert (
        response.status_code == 503
        and response.json()["code"] == "rate_limits_unavailable"
    )
    assert "synthetic cache outage" not in response.content.decode()
    assert response["Cache-Control"] == "private, no-store"


def test_public_catalog_and_session_reads_survive_cache_loss(client, monkeypatch):
    monkeypatch.setattr(LoginRateThrottle, "cache", unavailable_cache())
    assert client.get("/api/v1/catalog/books/").status_code == 200
    assert client.get("/api/v1/auth/session/").status_code == 200


def test_password_link_requests_cannot_bypass_their_quota_during_cache_loss(
    client, monkeypatch
):
    monkeypatch.setattr(PasswordLinkRateThrottle, "cache", unavailable_cache())
    response = client.post(
        "/api/v1/auth/password-links/inspect/",
        {"uid": "MQ", "token": "invalid"},
        content_type="application/json",
    )
    assert (
        response.status_code == 503
        and response.json()["code"] == "rate_limits_unavailable"
    )


def test_production_demo_login_is_disabled_without_creating_an_account(
    client, settings
):
    from apps.accounts.models import User

    settings.APP_ENV = "production"
    before = User.objects.count()
    assert client.get("/api/auth/demo-login/").status_code == 404
    assert User.objects.count() == before

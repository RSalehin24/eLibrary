import pytest
from apps.accounts.models import User
from django.test import Client

pytestmark = pytest.mark.django_db


def test_anonymous_login_requires_csrf_and_rotates_the_session():
    User.objects.create_user(
        email="csrf@example.com", password="correct-horse-battery-staple"
    )
    client = Client(enforce_csrf_checks=True)
    credentials = {
        "email": "csrf@example.com",
        "password": "correct-horse-battery-staple",
    }
    rejected = client.post(
            "/api/v1/auth/login/", credentials, content_type="application/json"
        )
    assert rejected.status_code == 403
    assert rejected.json()["code"] == "csrf_failed"
    assert rejected.json()["field_errors"] == {}
    assert rejected["Cache-Control"] == "private, no-store"
    session = client.get("/api/v1/auth/session/").json()
    response = client.post(
        "/api/v1/auth/login/",
        credentials,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=session["csrf_token"],
    )
    assert response.status_code == 200
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is True
    assert client.post("/api/v1/auth/logout/").status_code == 403
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    assert (
        client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code == 204
    )
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False

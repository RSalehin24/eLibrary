import json

import pytest

from apps.accounts.models import User
from apps.common.models import SavedFilter


@pytest.mark.django_db
def test_authenticated_user_can_create_list_and_delete_saved_filters(client):
    user = User.objects.create_user(email="filters@example.com", password="strong-password-123")
    client.force_login(user)

    created = client.post(
        "/api/saved-filters/",
        data=json.dumps(
            {
                "target": "catalog",
                "name": "Bangla Mysteries",
                "params": {"q": "রহস্য", "category": "উপন্যাস"},
            }
        ),
        content_type="application/json",
    )
    assert created.status_code == 201

    listed = client.get("/api/saved-filters/?target=catalog")
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Bangla Mysteries"
    assert SavedFilter.objects.filter(owner=user, target="catalog").count() == 1

    deleted = client.delete(f"/api/saved-filters/{created.json()['id']}/")
    assert deleted.status_code == 204

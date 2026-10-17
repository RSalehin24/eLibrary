import pytest
from apps.accounts.models import User
from apps.catalog.models import Book
from apps.common.models import LifecycleState
from django.utils import timezone

pytestmark = pytest.mark.django_db
OVERVIEW = "/api/v1/manage/overview/"


def test_legacy_unpublished_states_are_counted_without_manual_review(client):
    actor = User.objects.create_superuser(
        email="overview-states@library.test", password=None
    )
    for state in [
        LifecycleState.DRAFT,
        LifecycleState.NEEDS_REVIEW,
        LifecycleState.PROCESSING,
        LifecycleState.READY,
        LifecycleState.PUBLISHED,
        LifecycleState.ARCHIVED,
    ]:
        Book.objects.create(title=state, state=state)
    Book.objects.create(
        title="Removed", state=LifecycleState.SOFT_DELETED, deleted_at=timezone.now()
    )
    client.force_login(actor)
    counts = client.get(OVERVIEW).json()["books"]
    assert counts == {
        "total": 6,
        "draft": 2,
        "processing": 1,
        "ready": 1,
        "published": 1,
        "archived": 1,
        "editorial_pending": 0,
    }
    assert counts["total"] == sum(
        counts[state]
        for state in ["draft", "processing", "ready", "published", "archived"]
    )
    Book.objects.filter(state=LifecycleState.PUBLISHED).update(
        editorial_reviewed_at=timezone.now()
    )
    assert client.get(OVERVIEW).json()["books"] == counts


def test_empty_catalog_has_no_review_requirement(client):
    actor = User.objects.create_superuser(
        email="overview-empty@library.test", password=None
    )
    client.force_login(actor)
    assert client.get(OVERVIEW).json()["books"] == {
        "total": 0,
        "draft": 0,
        "processing": 0,
        "ready": 0,
        "published": 0,
        "archived": 0,
        "editorial_pending": 0,
    }

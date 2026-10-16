import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.management_access.services import update_managed_account
from apps.accounts.models import User
from apps.catalog.models import Book, Category
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .managed_access_fixtures import REFERENCES, account_url, grant_request

pytestmark = pytest.mark.django_db


def test_database_rejects_multiple_targets_even_without_a_serializer(accounts):
    book = Book.objects.create(title="একটি বই")
    category = Category.objects.create(name="একটি বিভাগ")
    with pytest.raises(IntegrityError), transaction.atomic():
        PermissionGrant.objects.create(
            user=accounts[1],
            scope=PermissionScope.READ_DURABLE,
            book=book,
            category=category,
        )


def test_missing_revisions_and_unknown_grant_fields_fail(client, accounts):
    target = accounts[1]
    assert (
        client.patch(
            account_url(target), {"full_name": "সংঘাত"}, content_type="application/json"
        ).status_code
        == 400
    )
    response = client.post(
        account_url(target) + "grants/",
        {**grant_request(), "user": accounts[0].pk},
        content_type="application/json",
    )
    assert response.status_code == 400 and "user" in response.json()["field_errors"]


def test_deleted_books_cannot_receive_new_permissions(client, accounts):
    book = Book.objects.create(title="অপসারিত", deleted_at=timezone.now())
    response = client.post(
        account_url(accounts[1]) + "grants/",
        {**grant_request(), "book": str(book.pk)},
        content_type="application/json",
    )
    assert response.status_code == 400 and "book" in response.json()["field_errors"]


def test_permissions_cannot_be_reactivated_over_an_opposing_or_duplicate_grant(
    client, accounts
):
    target = accounts[1]
    first = PermissionGrant.objects.create(
        user=target, scope=PermissionScope.READ_ONCE, is_active=False
    )
    PermissionGrant.objects.create(user=target, scope=PermissionScope.READ_DURABLE)
    endpoint = account_url(target) + f"grants/{first.pk}/"
    assert (
        client.patch(
            endpoint,
            {"expected_updated_at": first.updated_at.isoformat(), "is_active": True},
            content_type="application/json",
        ).status_code
        == 400
    )
    first.scope = PermissionScope.READ_DURABLE
    first.save()
    assert (
        client.patch(
            endpoint,
            {"expected_updated_at": first.updated_at.isoformat(), "is_active": True},
            content_type="application/json",
        ).status_code
        == 409
    )
    first.refresh_from_db()
    assert first.is_active is False


def test_grant_updates_cannot_move_identity_or_modify_full_control(client, accounts):
    target = accounts[1]
    grant = PermissionGrant.objects.create(
        user=target, scope=PermissionScope.SEND_KINDLE
    )
    endpoint = account_url(target) + f"grants/{grant.pk}/"
    response = client.patch(
        endpoint,
        {
            "expected_updated_at": grant.updated_at.isoformat(),
            "scope": PermissionScope.READ_DURABLE,
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    PermissionGrant.objects.create(
        user=target, scope=PermissionScope.ADMIN_FULL_CONTROL, is_active=False
    )
    protected = target.permission_grants.get(scope=PermissionScope.ADMIN_FULL_CONTROL)
    assert (
        client.patch(
            account_url(target) + f"grants/{protected.pk}/",
            {
                "expected_updated_at": protected.updated_at.isoformat(),
                "is_active": True,
            },
            content_type="application/json",
        ).status_code
        == 400
    )


def test_grants_cannot_be_updated_through_a_different_account_path(client, accounts):
    grant = PermissionGrant.objects.create(
        user=accounts[0], scope=PermissionScope.SEND_KINDLE
    )
    response = client.patch(
        account_url(accounts[1]) + f"grants/{grant.pk}/",
        {"expected_updated_at": grant.updated_at.isoformat(), "is_active": False},
        content_type="application/json",
    )
    assert response.status_code == 404


def test_access_services_recheck_fresh_account_status(accounts):
    actor, target = accounts
    User.objects.filter(pk=actor.pk).update(is_active=False)
    with pytest.raises(PermissionDenied):
        update_managed_account(
            actor,
            target.pk,
            {
                "expected_updated_at": target.updated_at.isoformat(),
                "full_name": "নিষিদ্ধ পরিবর্তন",
            },
        )


def test_superuser_can_manage_staff_reading_permissions_without_changing_roles(
    client, accounts
):
    actor, target = accounts
    actor.is_superuser = True
    actor.save()
    target.is_staff = True
    target.save()
    response = client.post(
        account_url(target) + "grants/",
        grant_request(PermissionScope.SEND_KINDLE),
        content_type="application/json",
    )
    assert response.status_code == 201
    target.refresh_from_db()
    assert target.is_staff and not target.is_superuser


def test_account_grant_and_reference_queries_stay_bounded_at_one_hundred(
    client, accounts, django_assert_max_num_queries
):
    target = accounts[1]
    for index in range(101):
        book = Book.objects.create(title=f"অনুমতির বই {index}")
        PermissionGrant.objects.create(
            user=target, book=book, scope=PermissionScope.READ_DURABLE
        )
    with django_assert_max_num_queries(6):
        response = client.get(account_url(target) + "grants/", {"limit": 100})
    assert len(response.json()["entries"]) == 100
    with django_assert_max_num_queries(5):
        response = client.get(REFERENCES, {"kind": "book", "limit": 100})
    assert len(response.json()["entries"]) == 100

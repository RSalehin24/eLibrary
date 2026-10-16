import json

from apps.accounts.models import User
from apps.catalog.editorial.service import EditorialConflict
from apps.catalog.locking import lock_title
from apps.catalog.models import Book
from apps.common.models import AuditLog, LifecycleState, ReviewState
from apps.common.permissions import user_can_create_catalog_book
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied


def require_catalog_creator(actor):
    if not user_can_create_catalog_book(actor):
        raise PermissionDenied("Global metadata management access is required.")


def existing_creation(actor, identifier, payload):
    audit = AuditLog.objects.filter(pk=identifier).first()
    if audit is None:
        return None
    if (
        audit.actor_id != actor.pk
        or audit.verb != "catalog.book.create"
        or audit.target_id != str(identifier)
        or audit.payload != payload
    ):
        raise EditorialConflict(
            "This request identifier belongs to a different creation."
        )
    return get_object_or_404(Book, pk=identifier, deleted_at__isnull=True)


def persist_creation(actor, identifier, values):
    with transaction.atomic():
        book = Book.objects.create(
            id=identifier,
            state=LifecycleState.NEEDS_REVIEW,
            review_state=ReviewState.NEEDS_REVIEW,
            **values,
        )
        AuditLog.objects.create(
            id=identifier,
            actor=actor,
            verb="catalog.book.create",
            target_type=Book._meta.label_lower,
            target_id=str(identifier),
            payload=json.loads(json.dumps(values, cls=DjangoJSONEncoder)),
        )
    return book


@transaction.atomic
def create_catalog_book(actor, attributes):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_catalog_creator(actor)
    values = dict(attributes)
    identifier = values.pop("operation_id")
    payload = json.loads(json.dumps(values, cls=DjangoJSONEncoder))
    existing = existing_creation(actor, identifier, payload)
    if existing is not None:
        return existing
    lock_title(values["title"])
    try:
        return persist_creation(actor, identifier, values)
    except IntegrityError as error:
        existing = existing_creation(actor, identifier, payload)
        if existing is not None:
            return existing
        raise EditorialConflict(
            "This record could not be created. Refresh the catalog."
        ) from error


def created_book(actor, identifier):
    require_catalog_creator(actor)
    get_object_or_404(
        AuditLog,
        pk=identifier,
        actor=actor,
        verb="catalog.book.create",
        target_type=Book._meta.label_lower,
        target_id=str(identifier),
    )
    return get_object_or_404(Book, pk=identifier, deleted_at__isnull=True)

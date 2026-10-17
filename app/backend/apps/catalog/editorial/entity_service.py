import json

from apps.accounts.models import User
from apps.catalog.editorial.creation import require_catalog_creator
from apps.catalog.editorial.entity_policy import entity_model, manageable_entities
from apps.catalog.editorial.service import EditorialConflict
from apps.catalog.locking import lock_title
from apps.catalog.models import Book, CollectionBook
from apps.common.models import AuditLog
from apps.common.text import normalize_catalog_text
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError


def entity_detail(actor, kind, identifier):
    entity = get_object_or_404(manageable_entities(actor, kind), pk=identifier)
    if kind == "collections":
        entity.ordered_books = list(
            entity.collection_books.select_related("book")
            .only("collection_id", "book_id", "book__title", "position")
            .order_by("position", "id")
        )
    return entity


def record_entity_change(actor, entity, verb):
    AuditLog.objects.create(
        actor=actor,
        verb=verb,
        target_type=entity._meta.label_lower,
        target_id=str(entity.pk),
    )


def replace_collection_books(entity, identifiers):
    books = Book.objects.filter(pk__in=identifiers, deleted_at__isnull=True)
    if books.count() != len(identifiers):
        raise ValidationError(
            {"book_ids": "One or more selected books are unavailable."}
        )
    entity.collection_books.all().delete()
    CollectionBook.objects.bulk_create(
        [
            CollectionBook(collection=entity, book_id=identifier, position=position)
            for position, identifier in enumerate(identifiers)
        ]
    )


def apply_entity_values(entity, kind, attributes):
    values = dict(attributes)
    identifiers = values.pop("book_ids", None)
    if identifiers is not None and kind != "collections":
        raise ValidationError(
            {"book_ids": "Only collections contain an ordered book selection."}
        )
    for name, value in values.items():
        setattr(entity, name, value)
    require_unique_entity_name(entity, kind)
    entity.editorial_reviewed_at = None
    entity.save()
    if identifiers is not None:
        replace_collection_books(entity, identifiers)


def require_unique_entity_name(entity, kind):
    if (
        entity_model(kind)
        .objects.exclude(pk=entity.pk)
        .filter(normalized_name=normalize_catalog_text(entity.name))
        .exists()
    ):
        raise ValidationError({"name": "An entity with this name already exists."})


def lock_entity_kind(kind):
    lock_title(f"catalog-entity:{kind}")


def locked_entity(actor, target, expected):
    kind, identifier = target
    entity = get_object_or_404(
        manageable_entities(actor, kind).select_for_update(), pk=identifier
    )
    if entity.updated_at != expected:
        raise EditorialConflict("The entity changed. Refresh it before continuing.")
    return entity


@transaction.atomic
def update_entity(actor, target, attributes):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    values = dict(attributes)
    lock_entity_kind(target[0])
    entity = locked_entity(actor, target, values.pop("expected_updated_at"))
    try:
        with transaction.atomic():
            apply_entity_values(entity, target[0], values)
    except IntegrityError as error:
        raise EditorialConflict("An entity with that name already exists.") from error
    record_entity_change(actor, entity, "catalog.entity.update")
    return entity


@transaction.atomic
def entity_command(actor, target, command):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    entity = locked_entity(actor, target, command["expected_updated_at"])
    action = command["action"]
    if action == "review":
        entity.editorial_reviewed_at = timezone.now()
    else:
        if target[0] != "collections":
            raise ValidationError(
                {"action": "Publication commands apply to collections."}
            )
        if action == "publish" and (
            not entity.editorial_description.strip()
            or not entity.collection_books.exists()
        ):
            raise EditorialConflict(
                "Add an introduction and select books before publication."
            )
        entity.state = "published" if action == "publish" else "archived"
    entity.save()
    record_entity_change(actor, entity, f"catalog.entity.{action}")
    return entity


def creation_replay(actor, target, payload):
    kind, identifier = target
    audit = AuditLog.objects.filter(pk=identifier).first()
    if audit is None:
        return None
    if (
        audit.actor_id != actor.pk
        or audit.verb != "catalog.entity.create"
        or audit.target_id != str(identifier)
        or audit.payload != payload
        or audit.target_type != entity_model(kind)._meta.label_lower
    ):
        raise EditorialConflict("This request identifier belongs to another command.")
    return get_object_or_404(entity_model(kind), pk=identifier)


def insert_entity(actor, target, values):
    kind, identifier = target
    model = entity_model(kind)
    entity = model(id=identifier, name=values["name"])
    apply_entity_values(entity, kind, values)
    return entity


@transaction.atomic
def create_entity(actor, kind, attributes):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_catalog_creator(actor)
    values = dict(attributes)
    identifier = values.pop("operation_id")
    payload = json.loads(json.dumps(values, cls=DjangoJSONEncoder))
    existing = creation_replay(actor, (kind, identifier), payload)
    if existing is not None:
        return existing
    lock_entity_kind(kind)
    try:
        with transaction.atomic():
            entity = insert_entity(actor, (kind, identifier), values)
            AuditLog.objects.create(
                id=identifier,
                actor=actor,
                verb="catalog.entity.create",
                target_type=entity._meta.label_lower,
                target_id=str(identifier),
                payload=payload,
            )
    except IntegrityError as error:
        existing = creation_replay(actor, (kind, identifier), payload)
        if existing is not None:
            return existing
        raise EditorialConflict(
            "The entity could not be created. Refresh its list."
        ) from error
    return entity

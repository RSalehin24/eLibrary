from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.catalog.serializers.public import DiscoveryParametersSerializer
from apps.common.models import SavedFilter
from apps.processing.job_serializers import JobParametersSerializer

CATALOG_FILTER_KEYS = {
    "q",
    "contributor",
    "contributor_role",
    "category",
    "series",
    "collection",
    "ownership",
    "record_type",
    "sort",
}
QUEUE_FILTER_KEYS = {
    "q",
    "view",
    "state",
    "kind",
    "book",
    "parent_job",
    "automation_run",
    "error_code",
    "coverage",
    "layout",
}
MAX_SAVED_FILTERS = 100


class SavedFilterConflict(APIException):
    status_code = 409
    default_code = "state_conflict"
    default_detail = (
        "A saved filter with this name or request identifier already exists."
    )


def validated_saved_parameters(target, parameters):
    allowed = CATALOG_FILTER_KEYS if target == "catalog" else QUEUE_FILTER_KEYS
    if set(parameters) - allowed:
        raise serializers.ValidationError({"params": "Choose supported filter fields."})
    serializer = (
        DiscoveryParametersSerializer(data=parameters)
        if target == "catalog"
        else JobParametersSerializer(data=parameters)
    )
    serializer.is_valid(raise_exception=True)
    return {key: serializer.data[key] for key in parameters}


@transaction.atomic
def create_saved_filter(actor, values):
    User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    params = validated_saved_parameters(values["target"], values["params"])
    existing = SavedFilter.objects.filter(pk=values["operation_id"]).first()
    if existing:
        if (
            existing.owner_id == actor.pk
            and existing.name == values["name"]
            and existing.target == values["target"]
            and existing.params == params
        ):
            return existing
        raise SavedFilterConflict()
    if (
        SavedFilter.objects.filter(owner=actor, target=values["target"]).count()
        >= MAX_SAVED_FILTERS
    ):
        raise serializers.ValidationError(
            {"name": "Remove a saved filter before creating another."}
        )
    try:
        with transaction.atomic():
            return SavedFilter.objects.create(
                id=values["operation_id"],
                owner=actor,
                name=values["name"],
                target=values["target"],
                params=params,
            )
    except IntegrityError as error:
        raise SavedFilterConflict() from error

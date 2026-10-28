import pytest
from apps.catalog.entity_identity import resolve_bound_entity
from apps.catalog.models import Contributor, EntitySourceBinding, Series
from django.db import IntegrityError, transaction

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("model", [Contributor, Series])
def test_display_names_do_not_merge_distinct_source_identities(model):
    first = resolve_bound_entity(model, "একই নাম", (model._meta.model_name, "first"))
    second = resolve_bound_entity(model, "একই নাম", (model._meta.model_name, "second"))
    assert first.pk != second.pk and first.slug != second.slug
    assert first.name == second.name == "একই নাম"
    assert first.catalog_code != second.catalog_code
    assert (
        resolve_bound_entity(model, "একই নাম", (model._meta.model_name, "first")).pk
        == first.pk
    )
    assert model.objects.count() == 2


@pytest.mark.parametrize("model", [Contributor, Series])
def test_an_unbound_display_name_is_not_proof_of_an_existing_identity(model):
    first = resolve_bound_entity(model, "একই নাম")
    assert resolve_bound_entity(model, "একই নাম").pk != first.pk
    assert not EntitySourceBinding.objects.exists()


def test_source_binding_cannot_silently_change_entity_kind():
    first = resolve_bound_entity(Contributor, "নাম", ("namespace", "identity"))
    with pytest.raises(ValueError):
        resolve_bound_entity(Series, "নাম", ("namespace", "identity"))
    assert EntitySourceBinding.objects.get().contributor == first
    assert not Series.objects.exists()


def test_binding_database_constraint_requires_one_real_entity():
    with pytest.raises(IntegrityError), transaction.atomic():
        EntitySourceBinding.objects.create(namespace="namespace", source_key="missing")


@pytest.mark.parametrize(
    "kind,model", [("contributors", Contributor), ("series", Series)]
)
def test_reference_search_distinguishes_equal_names_using_current_catalog_codes(
    kind, model
):
    from .entity_fixtures import entity_client

    _, client = entity_client()
    first = model.objects.create(name="একই নাম")
    second = model.objects.create(name="একই নাম")
    response = client.get(
        "/api/v1/manage/catalog-references/", {"kind": kind, "q": "একই নাম"}
    )
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert {entry["id"] for entry in entries} == {str(first.pk), str(second.pk)}
    assert {entry["catalog_code"] for entry in entries} == {
        first.catalog_code,
        second.catalog_code,
    }

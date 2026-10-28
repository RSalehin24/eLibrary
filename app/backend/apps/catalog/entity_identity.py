from django.db import transaction

from apps.catalog.locking import lock_title
from apps.catalog.models.entity_identity import EntitySourceBinding
from apps.common.text import clean_entity_display_text, normalize_catalog_text


@transaction.atomic
def resolve_bound_entity(model, name, identity=None):
    cleaned = clean_entity_display_text(name)
    if not normalize_catalog_text(cleaned):
        return None
    if identity is None:
        return model.objects.create(name=cleaned)
    namespace, source_key = identity
    lock_title(f"identity:{namespace}:{source_key}")
    field = "contributor" if model._meta.model_name == "contributor" else "series"
    binding = (
        EntitySourceBinding.objects.filter(namespace=namespace, source_key=source_key)
        .select_related(field)
        .first()
    )
    if binding:
        entity = getattr(binding, field)
        if entity is None:
            raise ValueError("The source identity belongs to another entity kind.")
        return entity
    entity = model.objects.create(name=cleaned)
    EntitySourceBinding.objects.create(
        namespace=namespace, source_key=source_key, **{field: entity}
    )
    return entity

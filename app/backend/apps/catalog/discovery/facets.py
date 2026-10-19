from django.db.models import Exists, Q

from apps.common.text import normalize_catalog_text


def matching_entity_ids(model, value):
    normalized = normalize_catalog_text(value)
    if not normalized:
        return model.objects.none().values("pk")
    exact_slug = model.objects.filter(slug=value)
    exact_name = model.objects.filter(normalized_name=normalized)
    names = Q(normalized_name=normalized) | (
        ~Exists(exact_name) & Q(normalized_name__contains=normalized)
    )
    matches = Q(slug=value) | (~Exists(exact_slug) & names)
    return model.objects.filter(matches).values("pk")

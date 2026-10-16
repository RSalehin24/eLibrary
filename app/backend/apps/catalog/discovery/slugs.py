from django.db.models import Q
from django.shortcuts import get_object_or_404


def catalog_object_by_slug(queryset, slug):
    return get_object_or_404(
        queryset.filter(Q(slug=slug) | Q(slug_history__slug=slug)).distinct()
    )

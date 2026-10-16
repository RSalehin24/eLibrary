from django.db.models import Q

from apps.common.text import unicode_slugify


def build_unique_slug(model, value, instance=None):
    max_length = model._meta.get_field("slug").max_length
    base_slug = (unicode_slugify(value or "") or "item")[:max_length]
    slug = base_slug
    counter = 2
    queryset = model.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    occupied = Q(slug=slug)
    has_history = any(
        field.name == "slug_history" for field in model._meta.get_fields()
    )
    while queryset.filter(
        occupied | Q(slug_history__slug=slug) if has_history else occupied
    ).exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[: max_length - len(suffix)]}{suffix}"
        occupied = Q(slug=slug)
        counter += 1

    return slug


def generated_asset_upload_to(instance, filename):
    return f"generated/{instance.book.slug}/{filename}"

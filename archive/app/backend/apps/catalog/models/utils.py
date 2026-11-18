from apps.common.text import unicode_slugify


def build_unique_slug(model, value, instance=None):
    base_slug = unicode_slugify(value or "") or "item"
    slug = base_slug
    counter = 2
    queryset = model.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def generated_asset_upload_to(instance, filename):
    return f"generated/{instance.book.slug}/{filename}"

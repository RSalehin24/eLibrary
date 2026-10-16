from django.db.models.signals import post_save, pre_save

from apps.catalog.models import Book, Category, Contributor, CuratedCollection, Series


def remember_previous_slug(sender, instance, **kwargs):
    fields = kwargs.get("update_fields")
    instance.previous_slug = None
    if kwargs.get("raw") or (fields is not None and "slug" not in fields):
        return
    instance.previous_slug = (
        sender.objects.select_for_update()
        .filter(pk=instance.pk)
        .values_list("slug", flat=True)
        .first()
    )


def store_slug_history(sender, instance, **kwargs):
    previous = getattr(instance, "previous_slug", None)
    if previous and previous != instance.slug and not kwargs.get("raw"):
        instance.slug_history.get_or_create(slug=previous)


def register_slug_history():
    for model in (Book, Category, Contributor, Series, CuratedCollection):
        pre_save.connect(
            remember_previous_slug,
            sender=model,
            dispatch_uid=f"{model._meta.label}.previous_slug",
        )
        post_save.connect(
            store_slug_history,
            sender=model,
            dispatch_uid=f"{model._meta.label}.slug_history",
        )

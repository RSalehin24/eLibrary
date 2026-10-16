def create_entity_fixture(identity, editor):
    from apps.access.models import PermissionGrant, PermissionScope
    from apps.catalog.models import Category, Contributor

    author = Contributor.objects.create(name=f"সীমিত লেখক {identity}")
    category = Category.objects.create(name=f"সীমিত বিভাগ {identity}")
    for field, entity in [("contributor", author), ("category", category)]:
        PermissionGrant.objects.create(
            user=editor, scope=PermissionScope.METADATA_EDIT, **{field: entity}
        )
    return {
        "contributor": {"id": str(author.pk), "name": author.name},
        "category": {"id": str(category.pk), "name": category.name},
    }

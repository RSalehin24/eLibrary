import re
import unicodedata

from django.db import migrations


def clean_display_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value))).strip()


def is_textual_character(char):
    return unicodedata.category(char).startswith(("L", "N", "M"))


def collapse_separators(value, separator=" "):
    pattern = re.escape(separator) + r"+"
    return re.sub(pattern, separator, value).strip(separator)


def normalize_catalog_text(value):
    text = clean_display_text(value).lower()
    normalized = []
    for char in text:
        if char.isspace():
            normalized.append(" ")
        elif is_textual_character(char):
            normalized.append(char)
    return collapse_separators("".join(normalized), " ")


def unicode_slugify(value):
    text = clean_display_text(value).lower()
    slug = []
    previous_was_separator = False

    for char in text:
        if is_textual_character(char):
            slug.append(char)
            previous_was_separator = False
            continue
        if char in {" ", "-", "_", "/", "|", ":", "–", "—"}:
            if slug and not previous_was_separator:
                slug.append("-")
                previous_was_separator = True

    return collapse_separators("".join(slug), "-")


def build_unique_slug(model, value, instance_pk):
    base_slug = unicode_slugify(value) or "item"
    slug = base_slug
    counter = 2

    while model.objects.exclude(pk=instance_pk).filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def backfill_unicode_safe_catalog_fields(apps, schema_editor):
    targets = [
        (apps.get_model("catalog", "Contributor"), "name", "normalized_name"),
        (apps.get_model("catalog", "Series"), "name", "normalized_name"),
        (apps.get_model("catalog", "Category"), "name", "normalized_name"),
        (apps.get_model("catalog", "Book"), "title", "normalized_title"),
    ]

    for model, name_field, normalized_field in targets:
        for instance in model.objects.all().order_by("created_at", "pk"):
            display_value = clean_display_text(getattr(instance, name_field))
            normalized_value = normalize_catalog_text(display_value)
            slug_value = build_unique_slug(model, display_value, instance.pk)
            updates = {}

            if getattr(instance, name_field) != display_value:
                updates[name_field] = display_value
            if getattr(instance, normalized_field) != normalized_value:
                updates[normalized_field] = normalized_value
            if getattr(instance, "slug") != slug_value:
                updates["slug"] = slug_value

            if updates:
                model.objects.filter(pk=instance.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_book_normalized_title_category_normalized_name_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_unicode_safe_catalog_fields, migrations.RunPython.noop),
    ]

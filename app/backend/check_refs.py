import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.catalog.models import Book, Category, Contributor, Series

try:
    from apps.catalog.views.references import annotate_reference_counts

    print("Successfully imported annotate_reference_counts!")
except ImportError:
    import traceback

    print("Failed to import annotate_reference_counts:")
    traceback.print_exc()

print("Categories total:", Category.objects.count())
print("Series total:", Series.objects.count())
print("Contributors total:", Contributor.objects.count())

book = Book.objects.filter(book_contributors__role="author").first()
if book:
    author = book.book_contributors.filter(role="author").first().contributor
    print(f"\nTesting with Author: {author.name}")

    cats = Category.objects.filter(
        books__book_contributors__contributor__name=author.name,
        books__book_contributors__role="author",
        books__deleted_at__isnull=True,
    ).distinct()
    print("Categories for this author (direct filter):", [c.name for c in cats])

    queryset = annotate_reference_counts(
        Category.objects.all(), "books", author=author.name
    ).filter(book_count__gt=0)
    print(
        "Categories for this author (via annotate_reference_counts):",
        [c.name for c in queryset],
    )
else:
    print("No books with authors found.")

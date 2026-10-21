import os


def create_layout_fixture(identity, book):
    from apps.catalog.models import BookSeries, Series

    series = Series.objects.create(name=f"বিন্যাস পরীক্ষার সিরিজ {identity}")
    BookSeries.objects.create(book=book, series=series)
    return {"series": {"id": str(series.pk), "slug": series.slug}}


def create_page_fixtures(identity, book):
    from seed_pagination import create_pagination_fixture

    specification = os.environ.get("FOUNDATION_BROWSER_SPECIFICATION")
    return {
        "layout": create_layout_fixture(identity, book)
        if specification == "design-layout.spec.mjs"
        else None,
        "pagination": create_pagination_fixture()
        if specification == "numbered-pagination.spec.mjs"
        else None,
    }

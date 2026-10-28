def create_personal_fixture(identity, books, create_account):
    from apps.access.models import PermissionGrant, PermissionScope
    from apps.catalog.models import (
        Book,
        BookCategory,
        BookContributor,
        BookGroup,
        BookSeries,
        Category,
        Contributor,
        Series,
        UserBook,
    )

    reader, account = create_account(identity, "personal-reader")
    paper = Book.objects.create(
        title=f"কাগজের বই {identity}",
        publisher="পরীক্ষার প্রকাশক",
        is_compilation=True,
        state="published",
    )
    UserBook.objects.create(user=reader, book=paper)
    private = Book.objects.create(title=f"অনুমতি পাওয়া ব্যক্তিগত বই {identity}")
    author = Contributor.objects.create(name=f"ব্যক্তিগত লেখক {identity}")
    category = Category.objects.create(name=f"ব্যক্তিগত বিভাগ {identity}")
    series = Series.objects.create(name=f"ব্যক্তিগত সিরিজ {identity}")
    BookContributor.objects.create(book=private, contributor=author, role="author")
    BookCategory.objects.create(book=private, category=category)
    BookSeries.objects.create(book=private, series=series)
    PermissionGrant.objects.create(
        user=reader, book=private, scope=PermissionScope.READ_DURABLE
    )
    group = BookGroup.objects.create(canonical_title=books[0].title)
    books[0].group = group
    books[0].save()
    sibling = Book.objects.create(
        title=f"অন্য প্রকাশিত সংস্করণ {identity}",
        group=group,
        edition="দ্বিতীয়",
        state="published",
    )
    Book.objects.create(title=f"গোপন সংস্করণ {identity}", group=group)
    return {
        "account": account,
        "paper": {"slug": paper.slug, "title": paper.title},
        "private": {"slug": private.slug, "title": private.title},
        "edition": {"slug": sibling.slug, "title": sibling.title},
    }

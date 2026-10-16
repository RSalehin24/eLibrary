def create_personal_fixture(identity, books, create_account):
    from apps.access.models import PermissionGrant, PermissionScope
    from apps.catalog.models import Book, BookGroup, UserBook

    reader, account = create_account(identity, "personal-reader")
    paper = Book.objects.create(
        title=f"কাগজের বই {identity}", record_type="manual", manual_publisher="পরীক্ষার প্রকাশক",
        manual_price="0.00", manual_binding="hard_cover", manual_is_compilation=True,
        state="published", review_state="approved",
    )
    UserBook.objects.create(user=reader, book=paper)
    private = Book.objects.create(title=f"অনুমতি পাওয়া ব্যক্তিগত বই {identity}")
    PermissionGrant.objects.create(user=reader, book=private, scope=PermissionScope.READ_DURABLE)
    group = BookGroup.objects.create(canonical_title=books[0].title)
    books[0].group = group
    books[0].save()
    sibling = Book.objects.create(title=f"অন্য প্রকাশিত সংস্করণ {identity}", group=group, edition="দ্বিতীয়", state="published", review_state="approved")
    Book.objects.create(title=f"গোপন সংস্করণ {identity}", group=group)
    return {"account": account, "paper": {"slug": paper.slug, "title": paper.title}, "private": {"slug": private.slug, "title": private.title}, "edition": {"slug": sibling.slug, "title": sibling.title}}

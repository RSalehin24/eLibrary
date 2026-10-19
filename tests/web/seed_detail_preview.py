def create_detail_preview_fixture(book, identity):
    from apps.catalog.models import BookContributor, Contributor

    for role, label in [("translator", "অনুবাদক"), ("editor", "সম্পাদক")]:
        contributor = Contributor.objects.create(name=f"পরীক্ষার {label} {identity}")
        BookContributor.objects.create(book=book, contributor=contributor, role=role)
    book.book_info_html = "<p>প্রকাশকাল: ২০২০</p>"
    book.dedication_html = "<p>পাঠকদের জন্য উৎসর্গ।</p>"
    nested = {"title": "শেষ উপাংশ"}
    for index in range(6, 0, -1):
        nested = {"title": f"উপাংশ {index}", "children": [nested]}
    book.toc = [{"title": "প্রথম খণ্ড", "children": [
        {"title": "প্রথম অধ্যায়", "children": [nested]},
    ]}]
    book.save(update_fields=["book_info_html", "dedication_html", "toc"])

import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Book, CuratedBookDocument
from apps.processing.models import BookRecord

targets = [
    ('রম্যরচনা ৩৬৫', 'https://www.ebanglalibrary.com/books/%e0%a6%b0%e0%a6%ae%e0%a7%8d%e0%a6%af%e0%a6%b0%e0%a6%9a%e0%a6%a8%e0%a6%be-%e0%a7%a9%e0%a7%ac%e0%a7%ab-%e0%a6%a4%e0%a6%be%e0%a6%b0%e0%a6%be%e0%a6%aa%e0%a6%a6-%e0%a6%b0%e0%a6%be%e0%a6%af%e0%a6%bc/'),
    ('বাংলা গীতা', 'https://www.ebanglalibrary.com/books/%e0%a6%ac%e0%a6%be%e0%a6%82%e0%a6%b2%e0%a6%be-%e0%a6%97%e0%a7%80%e0%a6%a4%e0%a6%be/'),
    ('মহাভারতের চরিতাবলী', 'https://www.ebanglalibrary.com/books/%e0%a6%ae%e0%a6%b9%e0%a6%be%e0%a6%ad%e0%a6%be%e0%a6%b0%e0%a6%a4%e0%a7%87%e0%a6%b0-%e0%a6%9a%e0%a6%b0%e0%a6%bf%e0%a6%a4%e0%a6%be%e0%a6%ac%e0%a6%b2%e0%a7%80/'),
    ('বাংলা কোরআন', 'https://www.ebanglalibrary.com/books/%e0%a6%ac%e0%a6%be%e0%a6%82%e0%a6%b2%e0%a6%be-%e0%a6%95%e0%a7%8b%e0%a6%b0%e0%a6%85%e0%a6%be%e0%a6%a8/'),
]

for name_pat, url in targets:
    print(f"\n==================================================")
    print(f"SEARCHING TARGET: {name_pat} | {url}")
    print(f"==================================================")
    
    # 1. BookRecord
    print("--- BookRecord ---")
    records = BookRecord.objects.filter(url__iexact=url)
    if not records.exists():
        # search by decoded or case insensitive pattern
        records = BookRecord.objects.filter(url__icontains=name_pat)
    for r in records:
        print(f"  Record ID: {r.id}")
        print(f"  Name: {r.name}")
        print(f"  URL: {r.url}")
        print(f"  State: {r.book_creation_state}")
        print(f"  Linked Book ID: {r.linked_book_id}")
    
    # 2. CuratedBookDocument
    print("--- CuratedBookDocument ---")
    docs = CuratedBookDocument.objects.filter(source_url__iexact=url)
    for d in docs:
        print(f"  Doc ID: {d.id}")
        print(f"  Title: {d.title}")
        print(f"  Status: {d.status}")
        print(f"  Book ID: {d.book_id}")
        print(f"  Validation Summary: {d.validation_summary}")
        
    # 3. Book
    print("--- Book ---")
    # We can match Book by title or slug
    slug_part = url.rstrip('/').split('/')[-1]
    books = Book.objects.filter(slug__iexact=slug_part)
    if not books.exists():
        books = Book.objects.filter(title__icontains=name_pat)
    for b in books:
        # count sections
        sec_count = b.curated_documents.first().sections.count() if b.curated_documents.exists() else 0
        print(f"  Book ID: {b.id}")
        print(f"  Title: {b.title}")
        print(f"  Slug: {b.slug}")
        print(f"  State: {b.state}")
        print(f"  Review State: {b.review_state}")
        print(f"  Curated Doc Section Count: {sec_count}")
        # print first few source_urls if it is a related manager
        try:
            urls_list = list(b.source_urls.values_list('url', flat=True))
            print(f"  Source URLs: {urls_list}")
        except Exception as e:
            print(f"  Source URLs field error: {e}")

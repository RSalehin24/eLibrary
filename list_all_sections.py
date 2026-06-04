import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Book, CuratedSection

b = Book.objects.get(title__icontains='রম্যরচনা')
doc = b.curated_documents.order_by('-created_at').first()
sections = list(CuratedSection.objects.filter(document=doc).order_by('sort_order'))

print(f"Book: {b.title}")
print(f"Total sections in DB: {len(sections)}")
print("-" * 50)
for idx, s in enumerate(sections):
    print(f"{idx+1}: Title='{s.title}' | Type={s.section_type} | Order={s.sort_order} | URL={s.source_url} | Content Len={len(s.html or '')}")

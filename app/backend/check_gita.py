import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.catalog.models import CuratedBookDocument

gita = CuratedBookDocument.objects.filter(source_url__contains="গীতা").first()
if gita:
    print(f"Title: {gita.title}")
    print(f"Status: {gita.status}")
    print(f"Structure Type: {gita.structure_type}")
    sections = list(gita.sections.order_by("sort_order", "section_id"))
    print(f"Number of Content Items: {len(sections)}")
    
    # Check first 10 sections details
    for i, section in enumerate(sections[:10]):
        print(f"Item {i+1}:")
        print(f"  title: {section.title}")
        print(f"  type: {section.section_type}")
        print(f"  path: {section.path}")
        print(f"  has_content: {bool(section.html)}")
        print(f"  content_len: {len(section.html or '')}")
        print(f"  source_url: {section.source_url}")
else:
    print("Gita book document not found in DB")

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.catalog.models import CuratedBookDocument

docs = CuratedBookDocument.objects.all()
print(f"Total CuratedBookDocuments: {docs.count()}")
for doc_obj in docs:
    doc = doc_obj.document or {}
    projection = doc.get("projection", {})
    content_items = projection.get("content_items", [])
    print("-" * 50)
    print(f"ID: {doc_obj.id}")
    print(f"Title: {doc_obj.title}")
    print(f"Source URL: {doc_obj.source_url}")
    print(f"Status: {doc_obj.status}")
    print(f"Structure Type: {doc_obj.structure_type}")
    print(f"Projection Content Items Count: {len(content_items)}")
    sections = doc.get("sections", [])
    print(f"Sections Count: {len(sections)}")
    # Print the titles of the first few content items to verify
    titles = [item.get("title") for item in content_items[:5]]
    print(f"First few content items: {titles}")

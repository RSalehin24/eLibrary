import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.processing.models import BookRecord

targets = ['রম্যরচনা-৩৬৫-তারাপদ-রায়', 'রম্যরচনা-৩৬৫', 'বাংলা-গীতা', 'বাংলা-কোরআন', 'মহাভারতের-চরিতাবলী']
for r in BookRecord.objects.all():
    url = r.url or ""
    # check targets or decoded/encoded variants
    match = False
    for t in targets:
        if t in url or t.lower() in url.lower():
            match = True
    if '%e0%a6%b0%e0%a6%ae%e0%a7%8d%e0%a6%af%e0%a6%b0%e0%a6%9a%e0%a6%a8%e0%a6%be' in url.lower():
        match = True
    if '%e0%a6%97%e0%a7%80%e0%a6%a4%e0%a6%be' in url.lower():
        match = True
    if '%e0%a6%95%e0%a7%8b%e0%a6%b0%e0%a6%85%e0%a6%be%e0%a6%a8' in url.lower():
        match = True
    if '%e0%a6%ae%e0%a6%b9%e0%a6%be%e0%a6%ad%e0%a6%be%e0%a6%b0%e0%a6%a4' in url.lower():
        match = True
        
    if match:
        print(f"Record: {r.name} | Linked Book: {r.linked_book} | State: {r.book_creation_state} | URL: {r.url}")

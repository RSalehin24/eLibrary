import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.ingestion.services.legacy_adapter import scrape_book_high_fidelity

URLS = [
    # লোহিতকিরণচ্ছটা – কোয়েল তালুকদার
    "https://www.example.com/books/%e0%a6%b2%e0%a7%8b%e0%a6%b9%e0%a6%bf%e0%a6%a4%e0%a6%95%e0%a6%bf%e0%a6%b0%e0%a6%a3%e0%a6%9a%e0%a7%8d%e0%a6%9b%e0%a6%9f%e0%a6%be-%e0%a6%95%e0%a7%8b%e0%a6%af%e0%a6%bc%e0%a7%87%e0%a6%b2-%e0%a6%a4/",
    # হাত ছুঁয়ে-ছুঁয়ে দিয়েছি সব
    "https://www.example.com/books/%e0%a6%b9%e0%a6%be%e0%a6%a4-%e0%a6%9b%e0%a7%81%e0%a6%81%e0%a6%af%e0%a6%bc%e0%a7%87-%e0%a6%9b%e0%a7%81%e0%a6%81%e0%a6%af%e0%a6%bc%e0%a7%87-%e0%a6%a6%e0%a6%bf%e0%a6%af%e0%a6%bc%e0%a7%87%e0%a6%9b/",
    # দুর্গরহস্য – শরদিন্দু বন্দ্যোপাধ্যায়
    "https://www.example.com/books/%E0%A6%A6%E0%A7%81%E0%A6%B0%E0%A7%8D%E0%A6%97%E0%A6%B0%E0%A6%B9%E0%A6%B8%E0%A7%8D%E0%A6%AF-%E0%A6%B6%E0%A6%B0%E0%A6%A6%E0%A6%BF%E0%A6%A8%E0%A7%8D%E0%A6%A6%E0%A7%81-%E0%A6%AC%E0%A6%A8%E0%A7%8D/",
]

for url in URLS:
    print(f"\n=== {url} ===")
    try:
        data = scrape_book_high_fidelity(url)
        print(f"  title: {data.get('book_title')}")
        print(f"  toc: {len(data.get('toc') or [])}")
        print(f"  content_items: {len(data.get('content_items') or [])}")
        print(f"  book_info len: {len(data.get('book_info') or '')}")
        print(f"  main_content len: {len(data.get('main_content') or '')}")
        for entry in (data.get('toc') or [])[:5]:
            print(f"    toc: {entry.get('title')}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ERROR: {e}")

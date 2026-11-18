import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.ingestion.pipeline.scraper_support.network import get_soup
from apps.ingestion.pipeline.book_manifest import extract_entry_content_html
from apps.ingestion.services.normalization import extract_main_content_segments, split_leading_front_sections

# দুর্গরহস্য
url = "https://www.example.com/books/%E0%A6%A6%E0%A7%81%E0%A6%B0%E0%A7%8D%E0%A6%97%E0%A6%B0%E0%A6%B9%E0%A6%B8%E0%A7%8D%E0%A6%AF-%E0%A6%B6%E0%A6%B0%E0%A6%A6%E0%A6%BF%E0%A6%A8%E0%A7%8D%E0%A6%A6%E0%A7%81-%E0%A6%AC%E0%A6%A8%E0%A7%8D/"
soup = get_soup(url)
content = extract_entry_content_html(soup, "")
print("=== দুর্গরহস্য ===")
print("entry_content len:", len(content))
book_info, dedication, residual = extract_main_content_segments(content)
print("book_info len:", len(book_info))
print("dedication len:", len(dedication))
print("residual len:", len(residual))
print("residual content:")
print(repr(residual[:500]))

print()

# লোহিতকিরণচ্ছটা
url2 = "https://www.example.com/books/%e0%a6%b2%e0%a7%8b%e0%a6%b9%e0%a6%bf%e0%a6%a4%e0%a6%95%e0%a6%bf%e0%a6%b0%e0%a6%a3%e0%a6%9a%e0%a7%8d%e0%a6%9b%e0%a6%9f%e0%a6%be-%e0%a6%95%e0%a7%8b%e0%a6%af%e0%a6%bc%e0%a7%87%e0%a6%b2-%e0%a6%a4/"
soup2 = get_soup(url2)
content2 = extract_entry_content_html(soup2, "")
print("=== লোহিতকিরণচ্ছটা ===")
print("entry_content len:", len(content2))
book_info2, dedication2, residual2 = extract_main_content_segments(content2)
print("book_info len:", len(book_info2))
print("dedication len:", len(dedication2))
print("residual len:", len(residual2))
print("residual content (first 300):")
print(repr(residual2[:300]))

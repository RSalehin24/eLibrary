import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from bs4 import BeautifulSoup
from apps.ingestion.pipeline.scraper_support.network import get_soup
from apps.ingestion.pipeline.book_manifest import extract_entry_content_html

url = "https://www.example.com/books/%E0%A6%A6%E0%A7%81%E0%A6%B0%E0%A7%8D%E0%A6%97%E0%A6%B0%E0%A6%B9%E0%A6%B8%E0%A7%8D%E0%A6%AF-%E0%A6%B6%E0%A6%B0%E0%A6%A6%E0%A6%BF%E0%A6%A8%E0%A7%8D%E0%A6%A6%E0%A7%81-%E0%A6%AC%E0%A6%A8%E0%A7%8D/"
soup = get_soup(url)
content = extract_entry_content_html(soup, "")
print("=== দুর্গরহস্য RAW CONTENT ===")
print(repr(content))
print()
print("=== লোহিতকিরণচ্ছটা RAW BLOCKS (first 15) ===")
url2 = "https://www.example.com/books/%e0%a6%b2%e0%a7%8b%e0%a6%b9%e0%a6%bf%e0%a6%a4%e0%a6%95%e0%a6%bf%e0%a6%b0%e0%a6%a3%e0%a6%9a%e0%a7%8d%e0%a6%9b%e0%a6%9f%e0%a6%be-%e0%a6%95%e0%a7%8b%e0%a6%af%e0%a6%bc%e0%a7%87%e0%a6%b2-%e0%a6%a4/"
soup2 = get_soup(url2)
content2 = extract_entry_content_html(soup2, "")
soup2p = BeautifulSoup(content2, "html.parser")
blocks = soup2p.find_all(["h1","h2","h3","h4","p","ul","ol"])
for i, b in enumerate(blocks[:15]):
    print(f"[{i}] <{b.name}> {repr(b.get_text(' ', strip=True)[:100])}")

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from bs4 import BeautifulSoup
from apps.ingestion.pipeline.scraper_support.network import get_soup
from apps.ingestion.pipeline.book_manifest import extract_entry_content_html
from apps.ingestion.services.normalization_modules.front_matter_detection import (
    is_dedication_heading, should_continue_dedication_block, is_body_section_marker
)
from apps.common.text import clean_display_text

# দুর্গরহস্য
url = "https://www.example.com/books/%E0%A6%A6%E0%A7%81%E0%A6%B0%E0%A7%8D%E0%A6%97%E0%A6%B0%E0%A6%B9%E0%A6%B8%E0%A7%8D%E0%A6%AF-%E0%A6%B6%E0%A6%B0%E0%A6%A6%E0%A6%BF%E0%A6%A8%E0%A7%8D%E0%A6%A6%E0%A7%81-%E0%A6%AC%E0%A6%A8%E0%A7%8D/"
soup = get_soup(url)
content = extract_entry_content_html(soup, "")
blocks = BeautifulSoup(content, "html.parser").find_all(
    ["h1","h2","h3","h4","h5","h6","p","ul","ol","blockquote","div"]
)

print("=== দুর্গরহস্য block walk ===")
in_dedication = False
for b in blocks:
    text = clean_display_text(b.get_text(" ", strip=True))
    dedic_head = is_dedication_heading(text, tag_name=b.name)
    if not in_dedication and dedic_head:
        in_dedication = True
        print(f"[DED_START] <{b.name}> {repr(text[:80])}")
    elif in_dedication:
        cont = should_continue_dedication_block(text, tag_name=b.name)
        body = is_body_section_marker(text, tag_name=b.name)
        marker = "CONTINUE" if cont else "STOP"
        print(f"  [{marker}] <{b.name}> body={body} {repr(text[:80])}")
    else:
        print(f"[RESIDUAL] <{b.name}> {repr(text[:80])}")

import json
import requests
from bs4 import BeautifulSoup

with open("/storage/ebangla_auth.json") as f:
    auth_data = json.load(f)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})
for cookie in auth_data["cookies"]:
    session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

base_url = "https://www.ebanglalibrary.com/books/%E0%A6%B0%E0%A6%AE%E0%A7%8D%E0%A6%AF%E0%A6%B0%E0%A6%9A%E0%A6%A8%E0%A6%BE-%E0%A7%A9%E0%A7%AC%E0%A7%AB-%E0%A6%A4%E0%A6%BE%E0%A6%B0%E0%A6%BE%E0%A6%AA%E0%A6%A6-%E0%A6%B0%E0%A6%BE%E0%A6%AF%E0%A6%BC/"

all_lessons = []
unique_hrefs = set()

for page in range(1, 20):
    url = f"{base_url}?ld-courseinfo-lesson-page={page}"
    print(f"Fetching: {url}")
    resp = session.get(url)
    if resp.status_code != 200:
        print(f"Error {resp.status_code}")
        break
        
    soup = BeautifulSoup(resp.text, "html.parser")
    page_links = []
    for a in soup.select("a"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if "/lessons/" in href:
            if href not in unique_hrefs:
                unique_hrefs.add(href)
                page_links.append({"title": title, "url": href})
                
    if not page_links:
        print(f"No new lesson links found on page {page}. Stopping.")
        break
        
    print(f"Page {page} added {len(page_links)} new lessons")
    all_lessons.extend(page_links)

print(f"\nTotal unique lessons found: {len(all_lessons)}")
for idx, lesson in enumerate(all_lessons):
    print(f"{idx+1}: {lesson['title']} -> {lesson['url']}")

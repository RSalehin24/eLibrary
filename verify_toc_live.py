import json
import requests
from bs4 import BeautifulSoup

# Load cookies
with open("/storage/ebangla_auth.json") as f:
    auth_data = json.load(f)

session = requests.Session()
# Set headers to look like a browser
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

for cookie in auth_data["cookies"]:
    session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

base_url = "https://www.ebanglalibrary.com/books/%E0%A6%B0%E0%A6%AE%E0%A7%8D%E0%A6%AF%E0%A6%B0%E0%A6%9A%E0%A6%A8%E0%A6%BE-%E0%A7%A9%E0%A7%AC%E0%A7%AB-%E0%A6%A4%E0%A6%BE%E0%A6%B0%E0%A6%BE%E0%A6%AA%E0%A6%A6-%E0%A6%B0%E0%a6%be%e0%a6%af%e0%a6%bc/"

all_chapters = []

for page in range(1, 10):
    if page == 1:
        url = base_url
    else:
        url = f"{base_url}page/{page}/"
        
    print(f"Fetching TOC Page {page}: {url}")
    resp = session.get(url)
    if resp.status_code == 404:
        print(f"Page {page} not found (404). Stopping.")
        break
    if resp.status_code != 200:
        print(f"Failed to fetch page {page}: status {resp.status_code}")
        break
        
    soup = BeautifulSoup(resp.text, "html.parser")
    # Find chapter links. In eBanglaLibrary, they are typically in a list under some specific class
    # Let's inspect the page content for links that look like chapter URLs
    links = []
    # Try different selector approaches
    for a in soup.select("article a, .entry-content a, .book-chapters a, .ld-lesson-list a, .ld-topic-list a"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if "/topics/" in href or "/lessons/" in href or "?ld-topic-page=" in href:
            if {"title": title, "url": href} not in links:
                links.append({"title": title, "url": href})
                
    if not links:
        # Fallback to any links within entry-content
        for a in soup.find_all("a"):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if "/topics/" in href and "/books/" not in href:
                if {"title": title, "url": href} not in links:
                    links.append({"title": title, "url": href})
                    
    print(f"Found {len(links)} links on Page {page}")
    for l in links:
        all_chapters.append(l)

print(f"\nTotal chapters parsed: {len(all_chapters)}")
for idx, ch in enumerate(all_chapters):
    print(f"{idx+1}: {ch['title']} -> {ch['url']}")

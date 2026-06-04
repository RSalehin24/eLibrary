import json
import requests
from bs4 import BeautifulSoup

# Load cookies
with open("/storage/ebangla_auth.json") as f:
    auth_data = json.load(f)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})
for cookie in auth_data["cookies"]:
    session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

course_url = "https://www.ebanglalibrary.com/books/%E0%A6%B0%E0%A6%AE%E0%A7%8D%E0%A6%AF%E0%A6%B0%E0%A6%9A%E0%A6%A8%E0%A6%BE-%E0%A7%A9%E0%A7%AC%E0%A7%AB-%E0%A6%A4%E0%A6%BE%E0%A6%B0%E0%A6%BE%E0%A6%AA%E0%A6%A6-%E0%A6%B0%E0%A6%BE%E0%A6%AF%E0%A6%BC/"

# Get landing page first to find nonce and course_id
resp = session.get(course_url)
soup = BeautifulSoup(resp.text, "html.parser")

pager = soup.find(class_="ld-pagination")
if not pager:
    print("No pager found!")
    exit(1)

nonce = pager.get("data-pager-nonce")
print("Nonce:", nonce)

# Find shortcode data
item_list = soup.select_one(".ld-item-list[data-shortcode-instance]") or soup.select_one(".ld-item-list[data-shortcode_instance]")
shortcode = {}
if item_list:
    shortcode_raw = item_list.get("data-shortcode-instance") or item_list.get("data-shortcode_instance") or "{}"
    shortcode = json.loads(shortcode_raw.replace("&quot;", '"'))

course_id = shortcode.get("course_id")
print("Course ID:", course_id)

pager_results = json.loads(pager.get("data-pager-results", "{}"))
total_pages = pager_results.get("total_pages", 8)
total_items = pager_results.get("total_items", 365)
print(f"Total Pages: {total_pages}, Total Items: {total_items}")

ajax_url = "https://www.ebanglalibrary.com/wp-admin/admin-ajax.php"
all_lessons = []

for page in range(1, total_pages + 1):
    params = {
        "action": "ld30_ajax_pager",
        "ld-courseinfo-lesson-page": page,
        "pager_nonce": nonce,
        "pager_results[paged]": 1,
        "pager_results[total_items]": total_items,
        "pager_results[total_pages]": total_pages,
        "context": "course_content_shortcode",
        "course_id": course_id,
        "shortcode_instance[course_id]": course_id,
        "shortcode_instance[post_id]": shortcode.get("post_id", course_id),
        "shortcode_instance[group_id]": shortcode.get("group_id", 0),
        "shortcode_instance[paged]": 1,
        "shortcode_instance[num]": shortcode.get("num", 50),
        "shortcode_instance[wrapper]": "true",
        "shortcode_instance[user_id]": shortcode.get("user_id", 0),
    }
    
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": course_url,
    }
    
    print(f"Fetching AJAX Page {page}...")
    ajax_resp = session.get(ajax_url, params=params, headers=headers)
    if ajax_resp.status_code != 200:
        print(f"Error fetching page {page}: {ajax_resp.status_code}")
        break
        
    payload = ajax_resp.json()
    markup = (payload.get("data") or {}).get("markup") or ""
    page_soup = BeautifulSoup(markup, "html.parser")
    
    page_lessons = []
    for a in page_soup.select("a"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if "/lessons/" in href:
            page_lessons.append({"title": title, "url": href})
            
    print(f"Page {page} returned {len(page_lessons)} lessons")
    all_lessons.extend(page_lessons)

print(f"\nTotal lessons fetched: {len(all_lessons)}")
for idx, lesson in enumerate(all_lessons):
    print(f"{idx+1}: {lesson['title']} -> {lesson['url']}")

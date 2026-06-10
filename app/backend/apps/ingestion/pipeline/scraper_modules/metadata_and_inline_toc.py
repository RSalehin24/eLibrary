
from apps.ingestion.services.resolution_support_metadata import split_display_title
from apps.ingestion.pipeline.scraper_support.network import _get_allowed_source_hosts

ASCII_TO_BANGLA_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _get_source_site_host():
    from django.conf import settings
    return (getattr(settings, "SOURCE_SITE_HOST", "") or "").strip().lower() or "www.example.com"


def normalize_structured_heading_title(title):
    cleaned = clean_display_text(title or "")
    if not cleaned:
        return ""
    return cleaned.translate(ASCII_TO_BANGLA_DIGITS)


def create_output_folder(book_title):
    base_folder = Path(settings.RUNTIME_STORAGE_DIR) / "media" / "scraped-books"
    if not base_folder.exists():
        base_folder.mkdir(parents=True, exist_ok=True)
        print(f"Created base folder: {base_folder}")

    folder_name = sanitize_folder_name(book_title)
    full_path = base_folder / folder_name

    if not full_path.exists():
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {full_path}")
    else:
        print(f"Folder already exists: {full_path}")

    return str(full_path)

def extract_title_and_author(soup):
    title_tag = soup.find("title")
    if not title_tag:
        return "Book Title", ""

    full_title = title_tag.get_text(" ", strip=True)
    return split_display_title(full_title)

def scrape_book_meta(soup):
    author = series = book_type = ""

    meta = soup.find("div", class_="entry-meta entry-meta-after-content")
    if not meta:
        return author, series, book_type

    def get_text(cls):
        span = meta.find("span", class_=cls)
        if not span:
            return ""
        # Get all <a> tags to handle multiple items
        links = span.find_all("a")
        if links:
            return ", ".join(link.get_text(strip=True) for link in links)
        return ""

    author = get_text("entry-terms-authors")
    series = get_text("entry-terms-series")
    book_type = get_text("entry-terms-ld_course_category")

    return author, series, book_type

def download_cover_image(soup, output_folder):
    figure = soup.find("figure", class_="entry-image-link entry-image-single")
    if not figure:
        return None

    img = figure.find("img")
    img_url = img.get("data-src") or img.get("src") if img else None

    if not img_url:
        source = figure.find("source")
        img_url = source.get("srcset").split()[0] if source else None

    if not img_url:
        return None

    try:
        with create_session_with_retries() as session:
            response = session.get(img_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    ext = ".webp" if ".webp" in img_url else ".jpg"
    filename = f"book_cover{ext}"
    
    with open(os.path.join(output_folder, filename), "wb") as f:
        f.write(response.content)

    return filename

def scrape_main_content(soup):
    container = (
        soup.select_one(".ld-tab-content.ld-visible.entry-content")
        or soup.select_one(".ld-tab-content.entry-content")
        or soup.select_one("article .entry-content")
        or soup.select_one(".entry-content")
    )
    if container:
        container = clean_buttons(container)
        content = container.decode_contents()
        content = remove_redundant_headers(content, "")
        return content
    return ""


def inline_toc_container(soup):
    top_level_tags = [child for child in soup.contents if isinstance(child, Tag)]
    if len(top_level_tags) == 1 and top_level_tags[0].name in {"div", "article", "section"}:
        return top_level_tags[0]
    return soup


def inline_toc_heading_text(block):
    return clean_display_text(block.get_text(" ", strip=True))


def is_inline_toc_heading(block):
    heading_text = inline_toc_heading_text(block)
    if not heading_text or len(heading_text) > 60:
        return False

    normalized_heading = normalize_text(heading_text)
    return any(normalize_text(pattern) == normalized_heading for pattern in INLINE_TOC_PATTERNS)


def extract_inline_toc_entries_from_list(list_block):
    entries = []

    for item in list_block.find_all("li", recursive=False):
        nested_list = item.find(["ul", "ol"], recursive=False)
        title_node = item.find("a") or item
        title = normalize_structured_heading_title(title_node.get_text(" ", strip=True))
        if not title:
            continue

        entry = {
            "title": title,
            "url": title_node.get("href") if title_node.name == "a" else "",
            "type": "lesson",
            "has_content": True,
        }
        if nested_list:
            children = extract_inline_toc_entries_from_list(nested_list)
            if children:
                entry["children"] = children

        entries.append(entry)

    return entries


def inline_content_heading_text(block):
    text = normalize_structured_heading_title(block.get_text(" ", strip=True))
    if not text or len(text) > 180:
        return ""

    if block.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return text

    strong_text = clean_display_text(
        " ".join(strong.get_text(" ", strip=True) for strong in block.find_all("strong"))
    )
    if strong_text and strong_text == text:
        return text

    return ""


def extract_inline_toc_and_content(main_content_html):
    if not main_content_html:
        return [], [], main_content_html

    soup = BeautifulSoup(main_content_html, "html.parser")
    container = inline_toc_container(soup)
    blocks = [child for child in list(container.children) if isinstance(child, Tag)]

    toc_heading_index = -1
    for index, block in enumerate(blocks):
        if is_inline_toc_heading(block):
            toc_heading_index = index
            break

    if toc_heading_index < 0:
        return [], [], main_content_html

    toc_entries = []
    toc_blocks = [blocks[toc_heading_index]]
    next_index = toc_heading_index + 1

    while next_index < len(blocks):
        block = blocks[next_index]
        if block.name not in {"ul", "ol"}:
            break
        toc_entries.extend(extract_inline_toc_entries_from_list(block))
        toc_blocks.append(block)
        next_index += 1

    if not toc_entries:
        # Fallback: paragraph-style TOC links (e.g. <p><a href="/lessons/...">title</a></p>)
        para_toc_index = next_index
        para_toc_entries = []
        para_toc_blocks = []
        while para_toc_index < len(blocks):
            block = blocks[para_toc_index]
            if block.name != "p":
                break
            links = block.find_all("a", href=True)
            if not links:
                break
            entries_from_block = []
            for a in links:
                url = normalize_crawl_url(a.get("href", ""))
                title = normalize_structured_heading_title(a.get_text(" ", strip=True))
                if url and title:
                    entries_from_block.append(
                        {"title": title, "url": url, "type": "lesson", "has_content": True}
                    )
            if not entries_from_block:
                break
            para_toc_entries.extend(entries_from_block)
            para_toc_blocks.append(block)
            para_toc_index += 1
        if para_toc_entries:
            toc_entries = para_toc_entries
            toc_blocks.extend(para_toc_blocks)
            next_index = para_toc_index

    if not toc_entries:
        return [], [], main_content_html

    content_items = []
    current_section = None
    for block in blocks[next_index:]:
        if block.parent is None:
            continue

        heading = inline_content_heading_text(block)
        if heading:
            if current_section and current_section["content_parts"]:
                content_items.append(
                    {
                        "title": current_section["title"],
                        "content": "\n".join(current_section["content_parts"]).strip(),
                        "type": "lesson",
                        "parent": None,
                    }
                )
            current_section = {"title": heading, "content_parts": []}
            block.decompose()
            continue

        if current_section is not None:
            current_section["content_parts"].append(str(block))
            block.decompose()

    if current_section and current_section["content_parts"]:
        content_items.append(
            {
                "title": current_section["title"],
                "content": "\n".join(current_section["content_parts"]).strip(),
                "type": "lesson",
                "parent": None,
            }
        )

    for block in toc_blocks:
        if block.parent is not None:
            block.decompose()

    return toc_entries, content_items, str(soup)


def normalize_crawl_url(url, base_url=""):
    if not url:
        return ""

    candidate = urljoin(base_url, str(url).strip()) if base_url else str(url).strip()
    parsed = urlparse(candidate)

    if parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.netloc.lower() not in _get_allowed_source_hosts():
        return ""

    normalized_path = parsed.path or "/"
    if normalized_path.startswith("/books/"):
        normalized_path = normalized_path.rstrip("/") + "/"

    return urlunparse(
        ("https", _get_source_site_host(), normalized_path, parsed.params, parsed.query, "")
    )

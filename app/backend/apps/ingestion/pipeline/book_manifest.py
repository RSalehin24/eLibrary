import json
import logging
import os
import re
import time
import unicodedata
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.pipeline import scraper
from apps.ingestion.pipeline.curated_extractors import (
    build_projection,
    classify_structure,
    extract_book_entities,
    extract_sections,
)
from apps.ingestion.pipeline.curated_validation import generated_toc_from_content_items
from apps.ingestion.pipeline.scraper_support.network import (
    HEADERS,
    clean_buttons,
    create_session_with_retries,
    decode_html_response,
    login_source_session,
    normalize_source_url,
)
from apps.ingestion.services.normalization import (
    classify_residual_main_content,
    dedupe_html_fragment_blocks,
    dedupe_structured_sections,
    extract_boundary_sections_from_content_items,
    extract_main_content_segments,
    format_book_info_html_ordered,
    infer_structured_content_from_main_content,
    merge_front_matter_html_parts,
    plain_text_from_html,
    promote_leading_front_matter,
    prune_duplicate_main_content,
    split_leading_front_sections,
    split_trailing_front_sections,
)
from apps.ingestion.services.resolution_support_metadata import split_display_title
from apps.ingestion.services.resolution_support_network import get_with_host_fallback
from apps.ingestion.pipeline.epub_properties.labels import detect_book_language, labels_for


def _get_source_site_host():
    from django.conf import settings
    return (getattr(settings, "SOURCE_SITE_HOST", "") or "").strip().lower() or "www.example.com"


logger = logging.getLogger(__name__)

CURRENT_MANIFEST_SCHEMA_VERSION = "2026-05-03.1"
UNCAPPED_LIMIT_KEYS = {"max_nodes", "max_lesson_pages", "max_topic_pages", "max_content_chars"}
SECTION_FALLBACK_TITLE = "অন্যান্য"
BANGLA_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def normalize_manifest_limits(content_limits=None):
    limits = {
        "max_nodes": None,
        "max_lesson_pages": None,
        "max_topic_pages": None,
        "max_content_chars": None,
        "disable_recursive": False,
        # Optional title of the expected final chapter.  When provided,
        # classify_manifest_structure() will verify the chapter is present in
        # the fetched TOC; if it is absent the book is marked content_incomplete
        # regardless of the numeric coverage threshold.
        "last_chapter_title": "",
    }
    if not isinstance(content_limits, dict):
        return limits

    for key in UNCAPPED_LIMIT_KEYS:
        raw_value = content_limits.get(key)
        if raw_value is None or raw_value == "" or raw_value == 0 or raw_value == "0":
            limits[key] = None
            continue
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            limits[key] = None
            continue
        limits[key] = parsed if parsed > 0 else None

    limits["disable_recursive"] = _as_bool(content_limits.get("disable_recursive", False))
    raw_last = content_limits.get("last_chapter_title", "")
    limits["last_chapter_title"] = clean_display_text(str(raw_last)) if raw_last else ""
    return limits


def bounded_total(total, limit):
    if not isinstance(total, int) or total < 1:
        total = 1
    if isinstance(limit, int) and limit > 0:
        return min(total, limit)
    return total


def truncate_html(html, max_content_chars):
    if not html:
        return ""
    if isinstance(max_content_chars, int) and max_content_chars > 0 and len(html) > max_content_chars:
        return html[:max_content_chars]
    return html


def build_query_url(base_url, query_updates):
    parsed = urlparse(base_url)
    current_query = parse_qs(parsed.query, keep_blank_values=True)
    for key, value in query_updates.items():
        current_query[key] = [str(value)]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(current_query, doseq=True),
            "",
        )
    )


def normalized_heading(title):
    cleaned = clean_display_text(title or "")
    if not cleaned:
        return ""
    cleaned = re.sub(r"\d+\s*Topics?.*$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned.translate(BANGLA_DIGITS)


def html_text(html):
    return clean_display_text(plain_text_from_html(html or ""))


# HTTP statuses that indicate a transient/rate-limit condition where the same
# URL is expected to succeed on a later attempt. The source site
# intermittently throttles rapid topic requests with these codes.
_TRANSIENT_HTTP_STATUSES = {429, 500, 502, 503, 504}
_FETCH_MAX_ATTEMPTS = 4
_FETCH_RETRY_BACKOFF = 2.0  # seconds; multiplied by attempt number


class SourceFetchContext:
    def __init__(self, session, *, sleep_seconds=0.5):
        self.session = session
        self.sleep_seconds = sleep_seconds
        self.pages = []
        self.cache = {}
        login_source_session(session)

    def fetch_soup(self, url, *, kind, title="", cache=True):
        if cache and url in self.cache:
            return self.cache[url]

        page = {
            "url": url,
            "kind": kind,
            "title": clean_display_text(title),
            "status": "failed",
            "status_code": None,
        }
        last_error = None
        for attempt in range(1, _FETCH_MAX_ATTEMPTS + 1):
            try:
                response = get_with_host_fallback(
                    self.session,
                    url,
                    headers=HEADERS,
                    timeout=60,
                )
                page["status_code"] = getattr(response, "status_code", None)
                if response.status_code == 200:
                    soup = BeautifulSoup(decode_html_response(response), "html.parser")
                    page["status"] = "fetched"
                    if not page["title"]:
                        page["title"] = page_title_from_soup(soup)
                    logger.info("Successfully fetched %s page %d: %s", kind, len(self.pages) + 1, url)
                    self.pages.append(page)
                    if cache:
                        self.cache[url] = soup
                    if self.sleep_seconds:
                        time.sleep(self.sleep_seconds)
                    return soup

                # Non-200: retry transient statuses with backoff, otherwise give up.
                if (
                    response.status_code in _TRANSIENT_HTTP_STATUSES
                    and attempt < _FETCH_MAX_ATTEMPTS
                ):
                    logger.warning(
                        "Transient HTTP %s for %s (attempt %d/%d) — retrying.",
                        response.status_code,
                        url,
                        attempt,
                        _FETCH_MAX_ATTEMPTS,
                    )
                    time.sleep(_FETCH_RETRY_BACKOFF * attempt)
                    continue
                self.pages.append(page)
                self.cache[url] = None
                return None
            except requests.exceptions.RequestException as error:
                last_error = error
                if attempt < _FETCH_MAX_ATTEMPTS:
                    logger.warning(
                        "Network error for %s (attempt %d/%d): %s — retrying.",
                        url,
                        attempt,
                        _FETCH_MAX_ATTEMPTS,
                        error,
                    )
                    time.sleep(_FETCH_RETRY_BACKOFF * attempt)
                    continue
                page["error"] = str(error)
                self.pages.append(page)
                if cache:
                    self.cache[url] = None
                return None

        # Exhausted all attempts on transient failures.
        if last_error is not None:
            page["error"] = str(last_error)
        self.pages.append(page)
        if cache:
            self.cache[url] = None
        return None


def page_title_from_soup(soup):
    title_tag = soup.find("title") if soup else None
    if not title_tag:
        return ""
    title, _author = split_display_title(title_tag.get_text(" ", strip=True))
    return clean_display_text(title)


def extract_title_and_author(soup):
    visible_title = soup.select_one("h1.entry-title")
    title = clean_display_text(visible_title.get_text(" ", strip=True)) if visible_title else ""
    title_author = ""
    title_tag = soup.find("title") if soup else None
    if title_tag:
        split_title, split_author = split_display_title(title_tag.get_text(" ", strip=True))
        title = title or split_title
        title_author = split_author
    return title or "Book Title", title_author


def class_tokens(tag):
    return set(tag.get("class") or []) if isinstance(tag, Tag) else set()


def has_class_token(tag, token):
    return token in class_tokens(tag)


def extract_entry_terms(soup):
    terms = {}
    meta = soup.select_one(".entry-meta.entry-meta-after-content") or soup.select_one(".entry-meta")
    if not meta:
        return terms

    for span in meta.find_all("span"):
        term_key = ""
        for token in class_tokens(span):
            if token.startswith("entry-terms-"):
                term_key = token.replace("entry-terms-", "", 1)
                break
        if not term_key:
            continue

        links = [clean_display_text(link.get_text(" ", strip=True)) for link in span.find_all("a")]
        values = [value for value in links if value]
        if not values:
            text = clean_display_text(span.get_text(" ", strip=True))
            if text:
                values = [text]
        if values:
            terms[term_key] = values
    return terms


def term_display(terms, *keys):
    values = []
    seen = set()
    for key in keys:
        for value in terms.get(key, []) or []:
            normalized = normalize_catalog_text(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            values.append(value)
    return ", ".join(values)


def first_srcset_url(value):
    if not value:
        return ""
    first = str(value).split(",")[0].strip()
    return first.split()[0] if first else ""


def extract_cover_url(soup, base_url):
    figure = (
        soup.select_one("figure.entry-image-link.entry-image-single")
        or soup.select_one("figure.entry-image-link")
        or soup.select_one("figure")
    )
    if not figure:
        return ""

    image = figure.find("img")
    candidates = []
    if image:
        candidates.extend(
            [
                image.get("data-src"),
                image.get("data-lazy-src"),
                image.get("src"),
                first_srcset_url(image.get("srcset")),
                first_srcset_url(image.get("data-srcset")),
            ]
        )

    for source in figure.find_all("source"):
        candidates.append(first_srcset_url(source.get("srcset")))

    for candidate in candidates:
        if candidate:
            return urljoin(base_url, candidate)
    return ""


def cover_extension(cover_url, content_type=""):
    path = urlparse(cover_url or "").path.lower()
    if ".webp" in path or "webp" in content_type:
        return ".webp"
    if ".png" in path or "png" in content_type:
        return ".png"
    if ".jpeg" in path or ".jpg" in path or "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    return ".jpg"


def download_cover_asset(cover_url, output_folder, session):
    if not cover_url or not output_folder:
        return ""
    try:
        response = session.get(cover_url, headers=HEADERS, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return ""

    ext = cover_extension(cover_url, response.headers.get("content-type", ""))
    filename = f"book_cover{ext}"
    os.makedirs(output_folder, exist_ok=True)
    with open(os.path.join(output_folder, filename), "wb") as handle:
        handle.write(response.content)
    return filename


def extract_entry_content_html(soup, title=""):
    if not soup:
        return ""
    candidates = (
        soup.select(".ld-tab-content.ld-visible.entry-content")
        or soup.select(".ld-tab-content.entry-content")
        or soup.select("article .entry-content")
        or soup.select(".entry-content")
    )
    if not candidates:
        return ""
    # Some LearnDash pages emit multiple .entry-content tab panels (e.g. a
    # "Bookmark" tab followed by the actual lesson content tab).  Pick the
    # candidate with the most text so we don't accidentally return the short
    # "Bookmark" panel instead of the real content.
    container = max(candidates, key=lambda el: len(el.get_text()))
    container = clean_buttons(container)
    html = container.decode_contents()
    return scraper.remove_redundant_headers(html, title)


def pagination_data(tag):
    if not tag or not tag.has_attr("data-pager-results"):
        return {}
    raw_value = tag.get("data-pager-results", "")
    try:
        return json.loads(raw_value.replace("&quot;", '"'))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def lesson_total_pages(soup):
    pagers = soup.select(".ld-pagination[data-pager-results]") if soup else []
    for pager in pagers:
        data = pagination_data(pager)
        context = clean_display_text(" ".join(pager.get("class", []))).lower()
        if "course_content" in context or data.get("pager_context") in {"course_content_shortcode", "course_content"}:
            try:
                return max(1, int(data.get("total_pages", 1)))
            except (TypeError, ValueError):
                return 1
    for pager in pagers:
        # Skip topic-level pagers that are nested inside a lesson/topic list item;
        # those paginate sub-topics within a lesson, not the course page itself.
        if pager.find_parent(class_="ld-item-lesson-item"):
            continue
        data = pagination_data(pager)
        if "total_pages" in data:
            try:
                return max(1, int(data.get("total_pages", 1)))
            except (TypeError, ValueError):
                return 1
    return 1


def topic_page_numbers(lesson_item, page_url, max_topic_pages=None):
    expand_id = lesson_item.get("data-ld-expand-id") if lesson_item else ""
    if not expand_id:
        return [1]

    # LearnDash stores the expand_id as "ld-expand-{lesson_id}" but the
    # ld-topic-page URL parameter and data-ld-topic-page attributes use only
    # the numeric lesson_id (e.g. "216992-2", not "ld-expand-216992-2").
    # Accept both formats so link-based detection works correctly.
    str_expand_id = str(expand_id)
    numeric_expand_id = str_expand_id[len("ld-expand-"):] if str_expand_id.startswith("ld-expand-") else str_expand_id
    valid_prefixes = {str_expand_id, numeric_expand_id}

    page_numbers = {1}
    for tag in lesson_item.find_all(href=True):
        parsed = urlparse(urljoin(page_url, tag.get("href", "")))
        for value in parse_qs(parsed.query).get("ld-topic-page", []):
            prefix, _, page_number = str(value).partition("-")
            if prefix not in valid_prefixes:
                continue
            try:
                page_numbers.add(int(page_number))
            except (TypeError, ValueError):
                continue

    for tag in lesson_item.find_all(attrs={"data-ld-topic-page": True}):
        prefix, _, page_number = str(tag.get("data-ld-topic-page", "")).partition("-")
        if prefix not in valid_prefixes:
            continue
        try:
            page_numbers.add(int(page_number))
        except (TypeError, ValueError):
            continue

    for pager in lesson_item.select(".ld-pagination[data-pager-results]"):
        data = pagination_data(pager)
        try:
            total_pages = int(data.get("total_pages", 1))
        except (TypeError, ValueError):
            continue
        page_numbers.update(range(1, bounded_total(total_pages, max_topic_pages) + 1))

    return sorted(page_number for page_number in page_numbers if page_number >= 1)


def find_lesson_item_by_expand_id(soup, expand_id):
    if not soup or not expand_id:
        return None
    return soup.find("div", attrs={"data-ld-expand-id": expand_id})


def topic_container_for_lesson(lesson_item):
    expand_id = lesson_item.get("data-ld-expand-id") if lesson_item else ""
    if expand_id:
        container = lesson_item.find("div", id=f"{expand_id}-container")
        if container:
            return container
    return lesson_item


def extract_topic_entries_from_lesson(lesson_item, *, base_url, seen_urls):
    container = topic_container_for_lesson(lesson_item)
    if not container:
        return []

    topics = []
    topic_items = container.find_all(
        "div",
        class_=lambda value: value and "ld-table-list-item" in value,
        recursive=True,
    )
    for topic_item in topic_items:
        anchor = topic_item.find(
            "a",
            class_=lambda value: value and "ld-table-list-item-preview" in value,
        )
        if anchor is None or not anchor.get("href"):
            continue
        topic_url = normalize_content_url(anchor.get("href"), base_url)
        key = topic_url or anchor.get("href")
        if key in seen_urls:
            continue
        seen_urls.add(key)

        title_span = anchor.find("span", class_="ld-topic-title")
        title = normalized_heading(
            title_span.get_text(" ", strip=True)
            if title_span is not None
            else anchor.get_text(" ", strip=True)
        )
        if not title:
            continue
        post_id = None
        item_id = topic_item.get("id") or ""
        match = re.search(r"ld-table-list-item-(\d+)", item_id)
        if match:
            post_id = match.group(1)
        else:
            for cls in topic_item.get("class", []):
                match2 = re.search(r"ld-topic-item-(\d+)", cls)
                if match2:
                    post_id = match2.group(1)
                    break
        topics.append(
            {
                "title": title,
                "url": topic_url,
                "type": "topic",
                "has_content": True,
                "post_id": post_id,
                "children": [],
            }
        )
    return topics



def scrape_nested_topic_nodes(lesson_item, page_url, ctx, limits, *, _meta=None):
    expand_id = lesson_item.get("data-ld-expand-id") if lesson_item else ""
    if not expand_id:
        return []

    topics = []
    seen_urls = set()
    for page_number in topic_page_numbers(
        lesson_item,
        page_url,
        limits.get("max_topic_pages") or limits.get("max_lesson_pages"),
    ):
        paged_lesson_item = lesson_item
        topic_page_url = page_url
        topic_soup = None
        if page_number > 1:
            if _meta is not None:
                _meta["has_topic_pagination"] = True
            # LearnDash's ld-topic-page URL parameter uses the numeric lesson ID,
            # not the full expand_id string (e.g. "216992-2", not "ld-expand-216992-2").
            lesson_id = expand_id[len("ld-expand-"):] if expand_id.startswith("ld-expand-") else expand_id
            topic_page_url = build_query_url(page_url, {"ld-topic-page": f"{lesson_id}-{page_number}"})
            topic_soup = ctx.fetch_soup(topic_page_url, kind="topic_toc_page", cache=False)
            paged_lesson_item = find_lesson_item_by_expand_id(topic_soup, expand_id)
            if paged_lesson_item is None:
                if topic_soup is not None:
                    topic_soup.decompose()
                continue

        topics.extend(
            extract_topic_entries_from_lesson(
                paged_lesson_item,
                base_url=topic_page_url,
                seen_urls=seen_urls,
            )
        )
        if topic_soup is not None:
            topic_soup.decompose()
    return topics


def normalize_content_url(url, base_url):
    if not url:
        return ""
    candidate = urljoin(base_url, str(url).strip())
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.netloc.lower() not in {_get_source_site_host(), f"www.{_get_source_site_host()}"}:
        return ""
    normalized_path = parsed.path or "/"
    if normalized_path.startswith("/books/"):
        normalized_path = normalized_path.rstrip("/") + "/"
    return urlunparse(("https", _get_source_site_host(), normalized_path, parsed.params, parsed.query, ""))


def toc_items_container(soup):
    if not soup:
        return None
    containers = soup.select(".ld-item-list.ld-lesson-list .ld-item-list-items")
    if containers:
        return containers[0]
    return soup.select_one(".ld-lesson-list")


def _scrape_embedded_lesson_page_toc(lesson_url, ctx, limits):
    """Fetch a lesson page and return any embedded sub-chapter TOC as topic nodes.

    Handles the "container lesson" pattern in the LearnDash sidebar navigation.
    On lesson pages, LearnDash renders a ``.ld-course-navigation`` sidebar with
    ``.ld-lesson-items`` containers:

    * One container lists the *course-level* lessons (the lesson's siblings in
      the book).  This container includes a ``ld-is-current-lesson`` item for
      the current page, so it is the course navigation — not sub-chapter
      content.
    * A *second* container (present only for "section" lessons that aggregate
      sub-chapters) lists the sub-chapters and contains **no**
      ``ld-is-current-lesson`` item.

    Regular leaf lessons have only the first (course-level) container, so this
    function returns [] and the lesson stays as a leaf node for
    ``fetch_content_item`` to collect later.

    Container lessons that also carry their own story text are handled
    correctly: the sub-chapter container is found regardless of whether story
    content is also present on the page.

    Returns a list of ``topic``-typed nodes when a sub-chapter container is
    found, or an empty list in all other cases.
    """
    lesson_soup = ctx.fetch_soup(lesson_url, kind="lesson_toc_check", cache=False)
    if not lesson_soup:
        return []

    nav = lesson_soup.select_one(".ld-course-navigation")
    if not nav:
        return []

    topics = []
    seen_urls: set = set()
    for lesson_list in nav.select(".ld-lesson-items"):
        # Skip the course-level navigation list — it marks the current lesson
        # with ld-is-current-lesson and lists the lesson's siblings, not its
        # sub-chapters.
        if lesson_list.select_one(".ld-is-current-lesson"):
            continue
        # This container holds sub-chapters of the current section lesson.
        for item in lesson_list.find_all(
            "div",
            class_=lambda c: c and "ld-lesson-item" in c,
            recursive=False,
        ):
            anchor = item.find("a")
            if anchor is None:
                continue
            title = normalized_heading(anchor.get_text(" ", strip=True))
            url = normalize_content_url(anchor.get("href", ""), lesson_url)
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            if not title:
                continue
            post_id = None
            item_id = item.get("id") or item.get("data-ld-expand-id") or ""
            match = re.search(r"ld-expand-(\d+)", str(item_id))
            if match:
                post_id = match.group(1)
            else:
                for cls in item.get("class", []):
                    match2 = re.search(r"ld-lesson-item-(\d+)", str(cls))
                    if match2:
                        post_id = match2.group(1)
                        break
            topics.append(
                {
                    "title": title,
                    "url": url,
                    "type": "topic",
                    "has_content": True,
                    "post_id": post_id,
                    "children": [],
                }
            )
    return topics


def parse_lesson_node(lesson_item, page_url, ctx, limits, *, _meta=None):
    anchor = lesson_item.find("a", class_=lambda value: value and "ld-item-name" in value)
    if anchor is None:
        return None
    title_node = anchor.find("div", class_=lambda value: value and "ld-item-title" in value) or anchor
    title = normalized_heading(title_node.get_text(" ", strip=True))
    url = normalize_content_url(anchor.get("href", ""), page_url)
    if not title and not url:
        return None
    topics = scrape_nested_topic_nodes(lesson_item, page_url, ctx, limits, _meta=_meta)
    # If no inline topic entries were found on the book page, check whether the
    # lesson page itself hosts an embedded LearnDash TOC (a "container lesson").
    # Books whose lesson items already have visible inline topics are unaffected
    # because scrape_nested_topic_nodes returns a non-empty list for them.
    if not topics and url:
        topics = _scrape_embedded_lesson_page_toc(url, ctx, limits)
    post_id = None
    expand_id = lesson_item.get("id") or lesson_item.get("data-ld-expand-id") or ""
    match = re.search(r"ld-expand-(\d+)", str(expand_id))
    if match:
        post_id = match.group(1)
    else:
        for cls in lesson_item.get("class", []):
            match2 = re.search(r"ld-lesson-item-(\d+)", str(cls))
            if match2:
                post_id = match2.group(1)
                break
    return {
        "title": title or url,
        "url": url,
        "type": "lesson",
        "has_content": True,
        "post_id": post_id,
        "children": topics,
    }


def section_heading_title(block):
    heading = block.select_one(".ld-lesson-section-heading") if block else None
    text = heading.get_text(" ", strip=True) if heading else block.get_text(" ", strip=True)
    return normalized_heading(text)


def _parse_tab_content_lesson_links(soup, page_url, ctx, limits):
    """Fallback TOC extraction for Gutenberg ld-tab-content format.

    Some books (e.g. using the Gutenberg block editor) place lesson links
    directly inside a ``div.ld-tab-content`` as paragraph links rather than
    in the standard ``.ld-lesson-list`` structure.  Extract those as plain
    lesson nodes.
    """
    tab = soup.select_one(".ld-tab-content")
    if not tab:
        return []
    seen_urls: set = set()
    nodes = []
    for anchor in tab.find_all("a"):
        href = anchor.get("href", "")
        if "/lessons/" not in href:
            continue
        url = normalize_content_url(href, page_url)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = normalized_heading(anchor.get_text(" ", strip=True))
        if not title:
            continue
        nodes.append(
            {
                "title": title,
                "url": url,
                "type": "lesson",
                "has_content": True,
                "children": [],
            }
        )
    return nodes


def parse_toc_nodes_from_page(soup, page_url, ctx, limits, *, _meta=None):
    container = toc_items_container(soup)
    if not container:
        return _parse_tab_content_lesson_links(soup, page_url, ctx, limits)

    nodes = []
    current_section = None
    children = [child for child in container.children if isinstance(child, Tag)]
    if not children:
        children = container.find_all("div", recursive=False)

    for child in children:
        if has_class_token(child, "ld-item-list-section-heading"):
            title = section_heading_title(child)
            if not title:
                continue
            current_section = {
                "title": title,
                "url": "",
                "type": "section",
                "has_content": False,
                "children": [],
            }
            nodes.append(current_section)
            continue

        lesson_item = child if has_class_token(child, "ld-item-lesson-item") else None
        if lesson_item is None:
            lesson_item = child.find(
                "div",
                class_=lambda value: value and "ld-item-lesson-item" in value,
                recursive=False,
            )
        if lesson_item is None:
            continue

        lesson_node = parse_lesson_node(lesson_item, page_url, ctx, limits, _meta=_meta)
        if lesson_node is None:
            continue
        if current_section is not None:
            current_section["children"].append(lesson_node)
        else:
            nodes.append(lesson_node)

    return [node for node in nodes if node.get("type") != "section" or node.get("children")]


def toc_node_key(node):
    return (
        normalize_catalog_text(node.get("url", "")),
        normalize_catalog_text(node.get("title", "")),
    )


def append_unique_child(container, child, seen_lesson_keys):
    key = toc_node_key(child)
    if key in seen_lesson_keys:
        return
    seen_lesson_keys.add(key)
    container.setdefault("children", []).append(child)


def mark_toc_subtree_seen(node, seen_lesson_keys):
    if node.get("type") != "section":
        seen_lesson_keys.add(toc_node_key(node))
    for child in node.get("children", []) or []:
        mark_toc_subtree_seen(child, seen_lesson_keys)


def append_toc_node(target, node, seen_lesson_keys, current_section):
    if node.get("type") == "section":
        title_key = normalize_catalog_text(node.get("title", ""))
        if current_section is not None and normalize_catalog_text(current_section.get("title", "")) == title_key:
            for child in node.get("children", []) or []:
                append_unique_child(current_section, child, seen_lesson_keys)
            return current_section
        target.append(node)
        mark_toc_subtree_seen(node, seen_lesson_keys)
        return node

    key = toc_node_key(node)
    if key in seen_lesson_keys:
        return current_section
    seen_lesson_keys.add(key)
    if current_section is not None:
        current_section.setdefault("children", []).append(node)
    else:
        target.append(node)
    return current_section


def _safe_referer(url):
    """Return a percent-encoded version of *url* safe for use as an HTTP Referer header.

    Python's ``http.client`` encodes header values as ``latin-1``, which raises
    ``UnicodeEncodeError`` for URLs that contain non-ASCII characters (e.g. Bengali
    script slugs).  Passing the URL through ``urllib.parse.quote`` first ensures
    the header value is pure ASCII.
    """
    # quote() leaves already-encoded percent-sequences and safe chars intact;
    # we keep the common URL punctuation unencoded so the header remains readable.
    return quote(url, safe=":/?=&#%@!$&'()*+,;~")


def _fetch_learndash_toc_page_ajax(ctx, landing_soup, course_url, page_number):
    """Fetch a LearnDash TOC page via the AJAX pager endpoint.

    The ``?ld-courseinfo-lesson-page=N`` GET parameter is ignored by the
    server for unauthenticated (and sometimes authenticated) requests; the
    only reliable path is the ``ld30_ajax_pager`` admin-ajax action used by
    the LearnDash JavaScript.

    Returns a BeautifulSoup of the lesson-list HTML on success, or None.
    """
    # Find a course-level pager (skip any pager nested inside a lesson item;
    # those paginate topics within a lesson, not the course page itself).
    pager = None
    if landing_soup:
        for candidate in landing_soup.select(".ld-pagination[data-pager-nonce]"):
            if not candidate.find_parent(class_="ld-item-lesson-item"):
                pager = candidate
                break
    if not pager:
        return None

    nonce = pager.get("data-pager-nonce", "")
    pager_data = pagination_data(pager)

    # Try both hyphenated and underscored attribute name variants.
    item_list = (
        landing_soup.select_one(".ld-item-list[data-shortcode_instance]")
        or landing_soup.select_one(".ld-item-list[data-shortcode-instance]")
    ) if landing_soup else None
    shortcode_raw = (
        (item_list.get("data-shortcode_instance") or item_list.get("data-shortcode-instance") or "{}")
        if item_list else "{}"
    )
    try:
        shortcode = json.loads(shortcode_raw.replace("&quot;", '"'))
    except (ValueError, json.JSONDecodeError):
        shortcode = {}

    course_id = shortcode.get("course_id") or pager_data.get("course_id")
    if not course_id or not nonce:
        return None

    ajax_url = f"https://{_get_source_site_host()}/wp-admin/admin-ajax.php"
    params = {
        "action": "ld30_ajax_pager",
        "ld-courseinfo-lesson-page": page_number,
        "pager_nonce": nonce,
        "pager_results[paged]": 1,
        "pager_results[total_items]": pager_data.get("total_items", 0),
        "pager_results[total_pages]": pager_data.get("total_pages", 1),
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
    # Use a percent-encoded Referer — Python's http.client encodes header values
    # as latin-1, which raises UnicodeEncodeError on Bengali-script URL slugs.
    headers = {
        **HEADERS,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": _safe_referer(course_url),
    }
    try:
        resp = ctx.session.get(ajax_url, params=params, headers=headers, timeout=60)
        if resp.status_code != 200:
            logger.warning(
                "LearnDash AJAX pager returned HTTP %s for page %s of %s",
                resp.status_code, page_number, course_url,
            )
            return None
        payload = resp.json()
        markup = (payload.get("data") or {}).get("markup") or ""
        if not markup:
            logger.debug(
                "LearnDash AJAX pager: empty markup for page %s of %s (payload keys: %s)",
                page_number, course_url, list(payload.keys()),
            )
            return None
        return BeautifulSoup(markup, "html.parser")
    except (requests.RequestException, ValueError, UnicodeError) as exc:
        logger.warning(
            "LearnDash AJAX pager failed for page %s of %s: %s",
            page_number, course_url, exc,
        )
        return None


def collect_learndash_toc(landing_soup, canonical_url, ctx, limits):
    if limits.get("disable_recursive"):
        return [], {
            "toc_page_count": 0,
            "has_paginated_toc": False,
            "has_section_headings": False,
            "source_total_pages": 1,
            "fetched_total_pages": 1,
            "toc_pages_with_content": 0,
            "toc_incomplete": False,
        }

    source_total_pages = lesson_total_pages(landing_soup)
    total_pages = bounded_total(source_total_pages, limits.get("max_lesson_pages"))
    collected = []
    seen_lesson_keys = set()
    current_section = None
    page_count = 0
    pages_with_content = 0
    _meta = {}

    for page_number in range(1, total_pages + 1):
        page_url = canonical_url if page_number == 1 else build_query_url(canonical_url, {"ld-courseinfo-lesson-page": page_number})
        if page_number == 1:
            soup = landing_soup
        else:
            # The ?ld-courseinfo-lesson-page=N GET parameter is ignored by the
            # server; use the AJAX pager action instead (requires auth cookies).
            soup = _fetch_learndash_toc_page_ajax(ctx, landing_soup, canonical_url, page_number)
            if soup is None:
                # Fallback to the GET parameter (may work on some configurations)
                soup = ctx.fetch_soup(page_url, kind="toc_page", cache=False)
        if not soup:
            continue
        page_count += 1
        keys_before = len(seen_lesson_keys)
        for node in parse_toc_nodes_from_page(soup, page_url, ctx, limits, _meta=_meta):
            if node.get("type") == "section":
                current_section = append_toc_node(collected, node, seen_lesson_keys, current_section)
                continue
            current_section = append_toc_node(collected, node, seen_lesson_keys, current_section)
        if len(seen_lesson_keys) > keys_before:
            pages_with_content += 1
        if page_number > 1 and soup is not None:
            soup.decompose()

    has_sections = any(node.get("type") == "section" for node in collected)
    has_topic_pagination = bool(_meta.get("has_topic_pagination"))
    # A multi-page TOC is "incomplete" when one or more of the pages we attempted
    # to fetch produced no new lessons. This is the signature of the LearnDash
    # AJAX pager being rejected (typically because the source site sign-in
    # cookie is missing or expired), so only the first page of lessons is captured.
    toc_incomplete = total_pages > 1 and pages_with_content < total_pages
    return collected, {
        "toc_page_count": page_count,
        "has_paginated_toc": total_pages > 1 or has_topic_pagination,
        "has_section_headings": has_sections,
        "source_total_pages": source_total_pages,
        "fetched_total_pages": total_pages,
        "toc_pages_with_content": pages_with_content,
        "toc_incomplete": toc_incomplete,
    }


def assign_paths_to_toc(nodes, parent_path=()):
    normalized_nodes = []
    for node in nodes or []:
        title = clean_display_text(node.get("title", ""))
        if not title:
            continue
        path = [*parent_path, title]
        children = assign_paths_to_toc(node.get("children", []), tuple(path))
        _raw_hc = node.get("has_content", True)
        normalized = {
            "title": title,
            "type": node.get("type") or "lesson",
            "has_content": _raw_hc if _raw_hc is None else bool(_raw_hc),
            "path": path,
        }
        if node.get("url"):
            normalized["source_url"] = node["url"]
        if node.get("post_id"):
            normalized["post_id"] = node["post_id"]
        if children:
            normalized["children"] = children
        normalized_nodes.append(normalized)
    return normalized_nodes


def iter_content_nodes(nodes, parent_path=()):
    for node in nodes or []:
        title = clean_display_text(node.get("title", ""))
        path = [*parent_path, title] if title else list(parent_path)
        if not node.get("children"):
            yield node, path
        yield from iter_content_nodes(node.get("children", []), tuple(path))


def duplicate_path_title(title, occurrence):
    suffix = str(occurrence).translate(BANGLA_DIGITS)
    return f"{title} ({suffix})"


def disambiguate_duplicate_content_paths(toc, content_items):
    # First pass: group items by clean path so we can detect duplicates and
    # decide between "rename" (genuine distinct items sharing a label) and
    # "merge" (identical inline extractions that should be collapsed).
    groups = {}
    item_order = []
    for index, item in enumerate(content_items or []):
        path = [clean_display_text(part) for part in item.get("path", []) if clean_display_text(part)]
        if not path:
            item_order.append((index, item, None))
            continue
        path_key = tuple(path)
        groups.setdefault(path_key, []).append(index)
        item_order.append((index, item, path_key))

    dropped_indices = set()
    updates_by_source_and_path = {}
    for path_key, indices in groups.items():
        if len(indices) < 2:
            continue
        items = [(content_items[i], i) for i in indices]
        source_urls = [(it.get("source_url") or "") for it, _ in items]
        # If every duplicate carries a distinct, non-empty source_url, treat
        # them as genuinely different chapters that happen to share a title
        # and disambiguate by appending an occurrence suffix.
        distinct_urls = all(source_urls) and len(set(source_urls)) == len(source_urls)
        if distinct_urls:
            for occurrence, (it, idx) in enumerate(items, start=1):
                if occurrence == 1:
                    continue
                updated_path = [*path_key[:-1], duplicate_path_title(path_key[-1], occurrence)]
                updates_by_source_and_path[(it.get("source_url") or "", path_key)] = updated_path
            continue
        # Otherwise the duplicates are inline-extraction artefacts (same URL
        # or no URL).  Keep the richest body text and drop the rest so the
        # curated document validates cleanly.
        def _body_len(entry):
            return len(plain_text_from_html(entry.get("content", "")) or "")
        keep_idx = max(indices, key=lambda i: _body_len(content_items[i]))
        for i in indices:
            if i != keep_idx:
                dropped_indices.add(i)

    normalized_items = []
    for index, item, path_key in item_order:
        if index in dropped_indices:
            continue
        normalized_item = dict(item)
        if path_key is not None:
            source_url = item.get("source_url") or ""
            updated_path = updates_by_source_and_path.get((source_url, path_key))
            if updated_path:
                normalized_item["title"] = updated_path[-1]
                normalized_item["path"] = updated_path
        normalized_items.append(normalized_item)

    # Build a set of surviving paths so we can prune TOC leaves that no
    # longer have an extracted content_item backing them.
    surviving_paths = set()
    for it in normalized_items:
        cleaned = tuple(
            clean_display_text(part)
            for part in it.get("path", [])
            if clean_display_text(part)
        )
        if cleaned:
            surviving_paths.add(cleaned)

    def update_toc_entries(entries):
        updated_entries = []
        seen_paths_local = set()
        for entry in entries or []:
            updated_entry = dict(entry)
            original_path = tuple(
                clean_display_text(part)
                for part in updated_entry.get("path", [])
                if clean_display_text(part)
            )
            source_url = updated_entry.get("source_url") or ""
            updated_path = updates_by_source_and_path.get((source_url, original_path))
            if updated_path:
                updated_entry["title"] = updated_path[-1]
                updated_entry["path"] = updated_path
                effective_path = tuple(updated_path)
            else:
                effective_path = original_path
            if updated_entry.get("children"):
                updated_entry["children"] = update_toc_entries(updated_entry["children"])
            # Drop a TOC leaf if its content was dropped as a duplicate AND
            # we have already seen an entry with the same effective path.
            if (
                effective_path
                and not updated_entry.get("children")
                and effective_path in seen_paths_local
                and effective_path in surviving_paths
            ):
                continue
            if effective_path:
                seen_paths_local.add(effective_path)
            updated_entries.append(updated_entry)
        return updated_entries

    return update_toc_entries(toc), normalized_items


# Sentinel returned when a page was fetched successfully but has no text content
# (the source chapter exists but is genuinely empty on the website).
# Distinct from None, which means the page could not be fetched at all.
_EMPTY_SOURCE_PAGE = object()


# LearnDash AJAX endpoint used for mark-complete submissions.
_LD_AJAX_URL = f"https://{_get_source_site_host()}/wp-admin/admin-ajax.php"


def _extract_mark_complete_params(soup):
    """Extract LearnDash mark-complete form inputs from a lesson/topic page soup.

    LearnDash gates sequential chapters behind a server-side check: lesson N+1
    is inaccessible until lesson N has been submitted via the ``sfwd_mark_complete``
    form.  This helper finds that form so the scraper can submit it.

    Returns a dict with ``post``, ``course_id``, ``nonce``, ``form_action``,
    and ``already_complete`` (True when the lesson has already been marked
    complete and the form field is ``sfwd_mark_incomplete`` instead).  Returns
    None when no LearnDash completion form is present on the page.
    """
    if not soup:
        return None
    for form in soup.find_all("form"):
        inputs = {
            inp.get("name"): inp.get("value", "")
            for inp in form.find_all("input")
            if inp.get("name")
        }
        # Capture the form's action URL so _submit_mark_complete can use it
        # as a fallback when the AJAX endpoint doesn't respond as expected.
        form_action = (form.get("action") or "").strip()
        if "sfwd_mark_complete" in inputs:
            return {
                "post": inputs.get("post", ""),
                "course_id": inputs.get("course_id", ""),
                "nonce": inputs["sfwd_mark_complete"],
                "form_action": form_action,
                "already_complete": False,
            }
        if "sfwd_mark_incomplete" in inputs:
            return {
                "post": inputs.get("post", ""),
                "course_id": inputs.get("course_id", ""),
                "nonce": inputs["sfwd_mark_incomplete"],
                "form_action": form_action,
                "already_complete": True,
            }
    return None


def _submit_mark_complete(session, lesson_url, mc_params):
    """Submit the LearnDash mark-complete action for ``lesson_url``.

    Submitting this tells the server that the user has read the chapter, which
    unlocks the next sequential chapter.  Only submits when the lesson has not
    already been marked complete (i.e. ``mc_params['already_complete']`` is
    False).

    LearnDash 3.x/4.x handles mark-complete exclusively via an AJAX POST to
    ``wp-admin/admin-ajax.php`` with ``action=sfwd_mark_complete`` and the
    ``X-Requested-With: XMLHttpRequest`` header.  A direct form POST to the
    lesson page URL (what was done previously) returns HTTP 200 but is silently
    ignored by the server — leaving the next chapter locked.

    Strategy:
    1. AJAX POST to ``_LD_AJAX_URL`` — primary path, validates JSON response.
    2. Direct form POST to ``lesson_url`` (or ``mc_params['form_action']`` if
       present) — fallback for older LearnDash configurations.

    Returns True when at least one approach appeared to succeed.
    """
    if not mc_params or mc_params.get("already_complete"):
        return False
    post_id = mc_params.get("post", "")
    course_id = mc_params.get("course_id", "")
    nonce = mc_params.get("nonce", "")
    if not (post_id and course_id and nonce):
        return False

    common_data = {
        "post": str(post_id),
        "course_id": str(course_id),
        "sfwd_mark_complete": nonce,
    }
    safe_referer = _safe_referer(lesson_url)

    # ------------------------------------------------------------------
    # Approach 1: LearnDash AJAX endpoint (primary)
    # LearnDash JS sends:  POST wp-admin/admin-ajax.php
    #   action=sfwd_mark_complete, post=<id>, course_id=<id>,
    #   sfwd_mark_complete=<nonce>
    # with X-Requested-With: XMLHttpRequest.
    # A successful response is JSON  {"success": true, ...}.
    # ------------------------------------------------------------------
    try:
        ajax_data = {"action": "sfwd_mark_complete", **common_data}
        resp = session.post(
            _LD_AJAX_URL,
            data=ajax_data,
            headers={
                **HEADERS,
                "Referer": safe_referer,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=60,
            allow_redirects=False,
        )
        if resp.status_code == 200:
            try:
                payload = resp.json()
                if payload.get("success"):
                    logger.info(
                        "Marked complete via AJAX: %s (post=%s)", lesson_url, post_id
                    )
                    return True
                # success=False means the server processed the request but
                # rejected it (e.g. bad nonce, wrong user).  Log and fall
                # through to the form-POST fallback.
                logger.warning(
                    "AJAX mark-complete returned success=False for %s — data=%s",
                    lesson_url,
                    payload,
                )
            except ValueError:
                # Non-JSON body: the AJAX endpoint may not recognise this
                # action on this site config.  Fall through to form POST.
                logger.debug(
                    "AJAX mark-complete returned non-JSON for %s (HTTP %s)",
                    lesson_url,
                    resp.status_code,
                )
        else:
            logger.warning(
                "AJAX mark-complete returned HTTP %s for %s",
                resp.status_code,
                lesson_url,
            )
    except (requests.exceptions.RequestException, UnicodeError) as exc:
        logger.warning("AJAX mark-complete request failed for %s: %s", lesson_url, exc)

    # ------------------------------------------------------------------
    # Approach 2: Direct form POST (fallback for older LearnDash configs)
    # Use the form's own action URL if available, otherwise the lesson URL.
    # ------------------------------------------------------------------
    form_action = (mc_params.get("form_action") or "").strip() or lesson_url
    try:
        resp = session.post(
            form_action,
            data=common_data,
            headers={
                **HEADERS,
                # Use a percent-encoded Referer so Bengali-script URLs don't
                # trigger a UnicodeEncodeError in Python's http.client.
                "Referer": safe_referer,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=60,
            allow_redirects=True,
        )
        success = resp.status_code == 200
        if success:
            logger.info(
                "Marked complete via form POST: %s (post=%s)", lesson_url, post_id
            )
        else:
            logger.warning(
                "Form-POST mark-complete returned HTTP %s for %s",
                resp.status_code,
                lesson_url,
            )
        return success
    except (requests.exceptions.RequestException, UnicodeError) as exc:
        logger.warning("Form-POST mark-complete failed for %s: %s", lesson_url, exc)
        return False


def _fetch_via_wp_rest_api(session, post_id, post_type="lesson"):
    """Fetch lesson or topic content via the WordPress REST API to bypass LearnDash lock."""
    segment = "sfwd-lessons" if post_type == "lesson" else "sfwd-topic"
    api_url = f"https://{_get_source_site_host()}/wp-json/ldlms/v2/{segment}/{post_id}"
    try:
        logger.info("Fetching locked content via WP REST API: %s (%s)", api_url, post_type)
        resp = session.get(api_url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            rendered = (data.get("content") or {}).get("rendered") or ""
            if rendered:
                wrapped_html = f'<div class="entry-content">{rendered}</div>'
                return BeautifulSoup(wrapped_html, "html.parser")
        else:
            logger.warning("WP REST API returned HTTP %s for post %s", resp.status_code, post_id)
    except Exception as exc:
        logger.warning("WP REST API query failed for post %s: %s", post_id, exc)
    return None


def fetch_content_item(node, path, ctx, limits):
    url = node.get("url", "")
    if not url:
        return None
    soup = ctx.fetch_soup(
        url,
        kind=node.get("type", "content"),
        title=node.get("title", ""),
        cache=False,
    )
    page_fetched = soup is not None

    # Extract mark-complete form params BEFORE decomposing the soup so we can
    # submit them after content extraction.
    mc_params = _extract_mark_complete_params(soup) if soup else None

    try:
        html = truncate_html(
            extract_entry_content_html(soup, node.get("title", "")),
            limits.get("max_content_chars"),
        )
    finally:
        if soup is not None:
            soup.decompose()

    if not html_text(html):
        # Try WP REST API fallback if content is empty (locked) and post_id is present
        post_id = node.get("post_id")
        if post_id:
            rest_soup = _fetch_via_wp_rest_api(ctx.session, post_id, node.get("type", "lesson"))
            if rest_soup:
                try:
                    html = truncate_html(
                        extract_entry_content_html(rest_soup, node.get("title", "")),
                        limits.get("max_content_chars"),
                    )
                finally:
                    rest_soup.decompose()

    if not html_text(html):
        # Content is empty (e.g. a locked/unread lesson that shows only the
        # "Bookmark" tab).  If the page exposed a ``sfwd_mark_complete`` form
        # the lesson IS accessible — submit the form so the next lesson unlocks,
        # then re-fetch to get the actual content.
        if mc_params and not mc_params.get("already_complete"):
            logger.info(
                "Content empty but mark-complete form found for %s — submitting and retrying.",
                url,
            )
            _submit_mark_complete(ctx.session, url, mc_params)
            time.sleep(1.0)  # brief pause for the server to record the change
            retry_soup = ctx.fetch_soup(
                url,
                kind=node.get("type", "content"),
                title=node.get("title", ""),
                cache=False,
            )
            retry_fetched = retry_soup is not None
            try:
                html = truncate_html(
                    extract_entry_content_html(retry_soup, node.get("title", "")),
                    limits.get("max_content_chars"),
                )
            finally:
                if retry_soup is not None:
                    retry_soup.decompose()
            if not html_text(html):
                return _EMPTY_SOURCE_PAGE if retry_fetched else None
        else:
            # Distinguish: page fetched OK but source has no text vs page unreachable.
            return _EMPTY_SOURCE_PAGE if page_fetched else None

    # Lesson has real content.  If it has not yet been marked complete, submit
    # the form now so that the next sequential lesson becomes accessible before
    # we attempt to fetch it.
    if mc_params and not mc_params.get("already_complete"):
        _submit_mark_complete(ctx.session, url, mc_params)

    return {
        "title": clean_display_text(node.get("title", "")),
        "content": html,
        "type": node.get("type") or "lesson",
        "parent": path[-2] if len(path) > 1 else None,
        "path": list(path),
        "source_url": url,
    }


def collect_content_items(nodes, ctx, limits, *, page_cache=None):
    content_items = []
    max_nodes = limits.get("max_nodes")
    cached = {}
    if page_cache is not None:
        cached = page_cache.get_cached_items()
        if cached:
            logger.info(
                "Resuming content scrape: %d pages already cached from previous run.",
                len(cached),
            )
    import gc
    for idx, (node, path) in enumerate(iter_content_nodes(nodes)):
        if idx > 0 and idx % 20 == 0:
            gc.collect()
        if isinstance(max_nodes, int) and max_nodes > 0 and len(content_items) >= max_nodes:
            break
        url = node.get("url", "")
        if url and url in cached:
            item = cached[url]
            # Preserve original has_content from the cached item dict;
            # fall back to bool check for legacy cache entries that lack the field.
            if isinstance(item, dict):
                cached_has_content = item.get("has_content", True) if item.get("content") else item.get("has_content")
                # Treat has_content=None placeholder same as truthy (reachable page)
                node["has_content"] = cached_has_content if cached_has_content is not None else None
                content_items.append(item)
            else:
                node["has_content"] = bool(item)
                if item:
                    content_items.append(item)
            continue
        item = fetch_content_item(node, path, ctx, limits)
        if item is _EMPTY_SOURCE_PAGE:
            # The page was reachable but has no text on the source website.
            # Keep the chapter in content_items as a placeholder so it still
            # appears in the EPUB TOC and spine (rendered as "unavailable").
            # It is NOT counted as missing for the completeness threshold.
            node["has_content"] = None
            placeholder = {
                "title": clean_display_text(node.get("title", "")),
                "content": "",
                "type": node.get("type") or "lesson",
                "parent": path[-2] if len(path) > 1 else None,
                "path": list(path),
                "source_url": url,
                "has_content": None,
            }
            if page_cache is not None:
                page_cache.save_item(placeholder)
            content_items.append(placeholder)
            continue
        if item is None:
            node["has_content"] = False
            continue
        node["has_content"] = True
        if page_cache is not None:
            page_cache.save_item(item)
        content_items.append(item)
    return content_items


def list_toc_structure_traits(nodes):
    lesson_count = 0
    topic_count = 0
    section_count = 0
    lessons_with_topics = 0
    lessons_without_topics = 0

    def walk(entries):
        nonlocal lesson_count, topic_count, section_count, lessons_with_topics, lessons_without_topics
        for entry in entries or []:
            entry_type = entry.get("type")
            children = entry.get("children", []) or []
            if entry_type == "section":
                section_count += 1
            elif entry_type == "topic":
                topic_count += 1
            else:
                lesson_count += 1
                if children:
                    lessons_with_topics += 1
                else:
                    lessons_without_topics += 1
            walk(children)

    walk(nodes)
    return {
        "lesson_count": lesson_count,
        "topic_count": topic_count,
        "section_count": section_count,
        "lessons_with_topics": lessons_with_topics,
        "lessons_without_topics": lessons_without_topics,
    }


def classify_manifest_structure(toc_nodes, content_items, main_content, toc_meta, limits=None):
    """Classify the structural shape of a fetched book and compute completeness.

    ``limits`` is the normalised content-limits dict produced by
    :func:`normalize_manifest_limits`.  When ``limits['last_chapter_title']``
    is set the function verifies that the named chapter appears somewhere in
    the fetched TOC or content items; if it is absent ``content_incomplete`` is
    forced to ``True`` regardless of the numeric coverage threshold.  This
    allows callers to pin a known terminal chapter (e.g. "স্বর্গ নরক" for
    রম্যরচনা ৩৬৫) so the system can reliably detect a partial fetch even when
    the missing tail falls inside the 5 % tolerance band.
    """
    traits = list_toc_structure_traits(toc_nodes)
    if not toc_nodes:
        if content_items:
            structure_type = "single_page_heading_split"
        elif html_text(main_content):
            structure_type = "single_page_flow_no_toc"
        else:
            structure_type = "no_public_body"
    elif traits["topic_count"] and traits["lessons_without_topics"]:
        structure_type = "mixed_lessons_and_topics"
    elif traits["topic_count"]:
        structure_type = "lesson_topic_nested"
    else:
        structure_type = "flat_lessons"

    if traits["section_count"] and structure_type in {"flat_lessons", "lesson_topic_nested", "mixed_lessons_and_topics"}:
        structure_type = f"sectioned_{structure_type}"

    # For flat-lesson books (no topics) the expected count is lessons; for
    # nested books it is topics; for mixed books it is topics + lessons without topics.
    topics_expected = traits["topic_count"] + (
        traits["lessons_without_topics"] if not traits["topic_count"] else 0
    )
    # A book is considered complete when it meets a minimum content threshold.
    # For small books (< 10 chapters): allow up to 33.33% of chapters missing.
    # For larger books: require at least 95% of chapters to have content.
    # Both empty-source pages (has_content=None) and failed fetches
    # (has_content=False) count as missing chapters.
    # Count only items that were actually fetched (including empty-source
    # placeholders with has_content=None). Items with has_content=False (truly
    # unreachable pages) are NOT in content_items and count as missing.
    topics_fetched = len(content_items) if content_items else 0
    topics_missing = topics_expected - topics_fetched
    if topics_expected == 0:
        content_incomplete = False
    elif topics_expected < 10:
        # Allow up to 33.33% missing (1-3 chapters for very small books)
        allowed_missing = max(1, topics_expected // 3)
        content_incomplete = topics_missing > allowed_missing
    else:
        # Allow up to 5% missing (95% threshold)
        allowed_missing = max(1, int(topics_expected * 0.05))
        content_incomplete = topics_missing > allowed_missing

    # --- last_chapter_title guard ------------------------------------------
    # When the caller specifies the title of the expected final chapter,
    # independently verify that it is present in the fetched data.  This
    # catches cases where the missing chapters fall within the 5 % tolerance
    # band (e.g. a book with 365 chapters where the last ~40 are missing but
    # numeric coverage happens to round above the threshold).
    if not content_incomplete and limits:
        last_chapter_title = clean_display_text(limits.get("last_chapter_title") or "")
        if last_chapter_title:
            normalized_target = normalize_catalog_text(last_chapter_title)
            # Build a set of all normalised chapter titles from both the TOC
            # node list and the fetched content items.
            fetched_titles = set()
            for _node, _path in iter_content_nodes(toc_nodes or []):
                t = normalize_catalog_text(clean_display_text(_node.get("title", "")))
                if t:
                    fetched_titles.add(t)
            for _item in content_items or []:
                t = normalize_catalog_text(clean_display_text(_item.get("title", "")))
                if t:
                    fetched_titles.add(t)
            if normalized_target and normalized_target not in fetched_titles:
                logger.warning(
                    "Expected last chapter %r not found in fetched TOC — "
                    "marking book as content_incomplete.",
                    last_chapter_title,
                )
                content_incomplete = True
    # -----------------------------------------------------------------------

    return {
        "type": structure_type,
        "traits": traits,
        "toc_page_count": toc_meta.get("toc_page_count", 0),
        "has_paginated_toc": toc_meta.get("has_paginated_toc", False),
        "has_section_headings": toc_meta.get("has_section_headings", False),
        "source_total_pages": toc_meta.get("source_total_pages", 1),
        "fetched_total_pages": toc_meta.get("fetched_total_pages", 1),
        "toc_pages_with_content": toc_meta.get("toc_pages_with_content", 0),
        "toc_incomplete": toc_meta.get("toc_incomplete", False),
        "content_incomplete": content_incomplete,
        "topics_expected": topics_expected,
        "topics_fetched": topics_fetched,
        "last_chapter_title": clean_display_text(limits.get("last_chapter_title") or "") if limits else "",
    }


_TITLE_PAGE_KEYWORDS = (
    "প্রকাশ",
    "প্রকাশক",
    "মুদ্রক",
    "সংস্করণ",
    "মূল্য",
    "publisher",
    "printer",
    "press",
    "edition",
    "published",
    "isbn",
    "copyright",
)


def _is_title_page_front_section(section, book_title, author):
    title = (section.get("title") or "").strip()
    # Named sections (preface, translator's note, etc.) are never a title page.
    if title:
        return False
    html = section.get("html") or ""
    text = plain_text_from_html(html).strip()
    if not text and not title:
        return False
    if len(text) > 1200:
        return False
    haystack = f"{title}\n{text}".lower()
    bt = (book_title or "").strip().lower()
    au = (author or "").strip().lower()
    title_match = bool(bt) and bt in haystack
    author_match = bool(au) and any(
        part for part in au.split() if len(part) >= 3 and part in haystack
    )
    if not title_match and not author_match:
        return False
    return any(keyword.lower() in haystack for keyword in _TITLE_PAGE_KEYWORDS)


# Normalized forms of common table-of-contents headings that a source page may
# include as a standalone section.  When the EPUB already has a generated TOC
# page, these inline-TOC front sections are redundant.
_INLINE_TOC_HEADING_NORMS = {
    normalize_catalog_text(h)
    for h in (
        "সূচিপত্র", "সূচী", "বিষয়সূচী", "বিষয় সূচী",
        "contents", "table of contents", "তালিকা",
    )
}


def _drop_inline_toc_front_sections(front_sections):
    """Remove any front section whose title is a table-of-contents heading.

    The EPUB builder already generates a dedicated toc.xhtml; keeping an
    inline TOC section would result in two identical "সূচিপত্র" nav entries.
    """
    result = []
    for s in front_sections:
        title = clean_display_text(s.get("title") or "")
        norm = normalize_catalog_text(title)
        if norm in _INLINE_TOC_HEADING_NORMS:
            continue
        result.append(s)
    return result


def _drop_chapter_title_front_sections(front_sections, toc):
    """Remove front sections whose titles duplicate a chapter/lesson name in the TOC.

    The source landing page sometimes lists lesson/chapter names as headings,
    which get extracted as front matter sections.  Since each such lesson
    already appears as a proper body chapter (with all its topics), keeping a
    tiny title-only front section would create an empty duplicate page in the
    EPUB.
    """
    if not front_sections or not toc:
        return front_sections
    lesson_norms = set()
    for entry in toc:
        title = clean_display_text(entry.get("title") or "")
        if title:
            lesson_norms.add(normalize_catalog_text(title))
    if not lesson_norms:
        return front_sections
    result = []
    for s in front_sections:
        title = clean_display_text(s.get("title") or "")
        norm = normalize_catalog_text(title)
        if norm and norm in lesson_norms:
            continue
        result.append(s)
    return result


def _is_pure_title_duplicate_section(section, book_title, author):
    """Return True when a section's entire text is just the book title (optionally
    followed by a separator, author, and/or series name in parentheses).

    Example: "যুগলবন্দী \u2013 নীহাররঞ্জন গুপ্ত (কিরীটী গোয়েন্দা কাহিনী)" is
    a single-line duplicate of the title page and should be silently dropped.
    """
    html = section.get("html") or ""
    text = plain_text_from_html(html).strip()
    if not text or len(text) > 350:
        return False
    bt = (book_title or "").strip()
    if not bt:
        return False

    def nfc(s):
        return unicodedata.normalize("NFC", s).strip()

    text_n = nfc(text)
    bt_n = nfc(bt)

    # Case 1: text starts with the book title
    if text_n.lower().startswith(bt_n.lower()):
        return True

    # Case 2: author-first format — "Author – Title" or "Author (Series) Title"
    au = (author or "").strip()
    if au:
        au_n = nfc(au)
        if text_n.lower().startswith(au_n.lower()) and bt_n.lower() in text_n.lower():
            return True

    # Case 3: bibliographic-only single line — e.g.
    # "সাতকাহন (১ম পর্ব) – উপন্যাস – সমরেশ মজুমদার". The text is short, has no
    # sentence-ending punctuation, and every separator-delimited fragment is
    # recognised as one of: a piece of the book title, the author, a known
    # book-type/genre keyword, an edition/volume marker, or pure
    # digits/parenthesised content. In that case the section adds no new
    # information beyond what book_info already carries.
    if _is_bibliographic_metadata_line(text_n, book_title=bt_n, author=au):
        return True

    return False


# Tokens that, on their own, are not new information when book_info is already
# present (book type / genre / format markers). Kept lowercase for matching.
_BIBLIOGRAPHIC_TOKEN_WORDS = {
    "উপন্যাস", "গল্প", "ছোটগল্প", "গল্পগ্রন্থ", "প্রবন্ধ", "কবিতা",
    "নাটক", "কাহিনি", "কাহিনী", "রচনাবলী", "সমগ্র", "অমনিবাস",
    "কিশোর", "ক্লাসিক", "সাহিত্য", "ইতিহাস", "দর্শন",
    "novel", "short story", "story", "stories", "poem", "poems",
    "essay", "essays", "drama", "novella", "omnibus", "edition", "vol", "volume",
    "part", "series",
}

# Suffix words used to mark editions/volumes — fragments containing only these
# (plus digits/Bengali digits/parens) are also acceptable as bibliographic.
_EDITION_MARKER_WORDS = {
    "খণ্ড", "পর্ব", "অধ্যায়", "সংস্করণ", "edition", "vol", "volume", "part", "ম",
}


def _is_bibliographic_metadata_line(text_n, *, book_title, author):
    """Heuristic: True when the line is purely a "title – type – author"-style
    bibliographic header that duplicates book_info."""

    if not text_n or len(text_n) > 200:
        return False
    # Multi-sentence / multi-paragraph content is real prose, not a header.
    if "\n" in text_n or text_n.count("।") > 1 or text_n.count(".") > 1:
        return False

    # Strip parenthesised pieces (edition markers like "(১ম পর্ব)" are noise).
    stripped = re.sub(r"[\(\[（【].*?[\)\]）】]", " ", text_n)
    stripped = re.sub(r"\s+", " ", stripped).strip(" -–—|/:.,")
    if not stripped:
        return False

    # Split on common bibliographic separators.
    fragments = [f.strip() for f in re.split(r"\s*[–—/|:]\s*|\s+[-]\s+", stripped) if f.strip()]
    if not fragments:
        return False

    bt_low = (book_title or "").lower()
    au_low = (author or "").lower()
    # Tokenised title pieces to match a fragment like "সাতকাহন" against title
    # "সাতকাহন ১".
    bt_tokens = {tok for tok in re.split(r"\s+", bt_low) if len(tok) >= 3}
    au_tokens = {tok for tok in re.split(r"\s+", au_low) if len(tok) >= 3}

    def fragment_is_metadata(frag):
        f = frag.lower().strip(" -–—|/:.,")
        if not f:
            return True
        if bt_low and (f == bt_low or f in bt_low or bt_low in f):
            return True
        if au_low and (f == au_low or au_low in f or f in au_low):
            return True
        # Pure digits / Bengali digits.
        if re.fullmatch(r"[0-9০-৯\s.\-]+", f):
            return True
        if f in _BIBLIOGRAPHIC_TOKEN_WORDS:
            return True
        # All words of fragment recognised as bibliographic / edition / digit.
        words = [w for w in re.split(r"\s+", f) if w]
        if words and all(
            w in _BIBLIOGRAPHIC_TOKEN_WORDS
            or w in _EDITION_MARKER_WORDS
            or w in bt_tokens
            or w in au_tokens
            or re.fullmatch(r"[0-9০-৯.\-]+", w)
            for w in words
        ):
            return True
        return False

    # Require at least one fragment to match the title (so we don't drop an
    # unrelated short line like "ভূমিকা") AND at least one fragment to match
    # the author (so we don't drop legitimate one-line standalone content).
    has_title_match = False
    has_author_match = False
    for frag in fragments:
        if not fragment_is_metadata(frag):
            return False
        f = frag.lower().strip(" -–—|/:.,")
        if bt_low and (f == bt_low or f in bt_low or bt_low in f or any(t in f for t in bt_tokens)):
            has_title_match = True
        if au_low and (f == au_low or au_low in f or f in au_low or any(t in f for t in au_tokens)):
            has_author_match = True
    return has_title_match and has_author_match


def _promote_title_page_front_sections_to_book_info(
    *, book_info, front_sections, book_title, author
):
    """Move publisher/printer info found in a title-page front section into
    book_info. Title-page front sections (e.g. সতী's first front section)
    typically duplicate the book title + author but also carry the only copy
    of publisher/printer/edition lines — those belong in Book Information.
    """

    if not front_sections:
        return book_info, front_sections

    bt_norm = (book_title or "").strip().lower()
    au_norm = (author or "").strip().lower()

    kept_sections = []
    extra_lines_html = []

    for section in front_sections:
        if not _is_title_page_front_section(section, book_title, author):
            # Drop sections that are nothing but a title/author/series line.
            if not _is_pure_title_duplicate_section(section, book_title, author):
                kept_sections.append(section)
            continue

        html = section.get("html") or ""
        # Split the HTML into <p>...</p> blocks; fall back to line splitting.
        blocks = re.findall(r"<p[^>]*>.*?</p>", html, flags=re.IGNORECASE | re.DOTALL)
        if not blocks:
            blocks = [
                f"<p>{line.strip()}</p>"
                for line in plain_text_from_html(html).splitlines()
                if line.strip()
            ]
        for block in blocks:
            block_text = plain_text_from_html(block).strip()
            if not block_text:
                continue
            bl = block_text.lower()
            if bt_norm and bl == bt_norm:
                continue
            if au_norm and bl == au_norm:
                continue
            # Drop blocks that are just "title – author" duplicates.
            if bt_norm and au_norm and bt_norm in bl and au_norm in bl and len(block_text) <= len(book_title) + len(author) + 6:
                continue
            extra_lines_html.append(block)

    if extra_lines_html:
        appended = "\n".join(extra_lines_html)
        book_info = merge_front_matter_html_parts(book_info or "", appended)

    return book_info, kept_sections


def normalize_body_sections(
    *,
    book_title,
    landing_main_content,
    toc_nodes,
    content_items,
    author="",
    series="",
    book_type="",
):
    book_info, dedication, residual_main = extract_main_content_segments(landing_main_content or "")
    book_info = dedupe_html_fragment_blocks(book_info)
    dedication = dedupe_html_fragment_blocks(dedication)

    front_sections = []
    back_sections = []
    has_explicit_body = bool(toc_nodes or content_items)
    leading_sections, residual_main = split_leading_front_sections(
        residual_main or "",
        has_explicit_body=has_explicit_body,
    )
    front_sections.extend(leading_sections)

    toc = assign_paths_to_toc(toc_nodes)
    has_structured_content = bool(toc or content_items)

    if not has_structured_content:
        inferred_toc, inferred_content_items, residual_main = infer_structured_content_from_main_content(
            residual_main or "",
            book_title=book_title,
        )
        if inferred_toc and inferred_content_items:
            toc = inferred_toc
            content_items = inferred_content_items
            has_structured_content = True

    if content_items:
        inferred_front, inferred_back, toc, content_items = extract_boundary_sections_from_content_items(
            content_items,
            toc,
            trust_source_toc=has_explicit_body,
        )
        front_sections.extend(inferred_front)
        back_sections.extend(inferred_back)
        toc, content_items = disambiguate_duplicate_content_paths(toc, content_items)

    if not has_explicit_body:
        trailing_sections, residual_main = split_trailing_front_sections(residual_main or "")
        back_sections.extend(trailing_sections)

    front_sections = dedupe_structured_sections(
        front_sections,
        reference_fragments=[book_info, dedication],
    )
    back_sections = dedupe_structured_sections(
        back_sections,
        reference_fragments=[book_info, dedication],
    )
    residual_main = prune_duplicate_main_content(
        residual_main,
        reference_fragments=[
            book_info,
            dedication,
            *[section.get("html", "") for section in front_sections],
            *[section.get("html", "") for section in back_sections],
        ],
        content_items=content_items,
    )

    # Classify any remaining residual main content. New key:value metadata is
    # merged into book_info; coherent prose is wrapped under an auto-generated
    # heading and appended as a front section; anything else is discarded.
    if has_structured_content and html_text(residual_main):
        residual_book_info, residual_sections, residual_main = classify_residual_main_content(
            residual_main,
            existing_fragments=[
                book_info,
                dedication,
                *[section.get("html", "") for section in front_sections],
                *[section.get("html", "") for section in back_sections],
                *[item.get("content", "") for item in (content_items or [])],
            ],
        )
        if residual_book_info:
            book_info = merge_front_matter_html_parts(book_info, residual_book_info)
        if residual_sections:
            front_sections.extend(residual_sections)
            front_sections = dedupe_structured_sections(
                front_sections,
                reference_fragments=[book_info, dedication],
            )

    if book_info:
        promoted_info, front_sections = _promote_title_page_front_sections_to_book_info(
            book_info=book_info,
            front_sections=front_sections,
            book_title=book_title,
            author=author,
        )
        book_info = promoted_info
    else:
        # Even with no book_info, drop sections whose content is nothing but the
        # book title / author / series line (pure title-page duplicates).
        front_sections = [
            s for s in front_sections
            if not _is_pure_title_duplicate_section(s, book_title, author)
        ]

    language = detect_book_language(
        book_title=book_title or "",
        author=author or "",
        book_info_html=book_info or "",
    )

    if not book_info:
        fallback_lines = []
        if language == "en":
            if book_title:
                fallback_lines.append(f"<p>Title: {book_title}</p>")
            if author:
                fallback_lines.append(f"<p>Author: {author}</p>")
            if series:
                fallback_lines.append(f"<p>Series: {series}</p>")
            if book_type:
                fallback_lines.append(f"<p>Type: {book_type}</p>")
        else:
            if book_title:
                fallback_lines.append(f"<p>শিরোনাম: {book_title}</p>")
            if author:
                fallback_lines.append(f"<p>লেখক: {author}</p>")
            if series:
                fallback_lines.append(f"<p>সিরিজ: {series}</p>")
            if book_type:
                fallback_lines.append(f"<p>বইয়ের ধরন: {book_type}</p>")
        book_info = "\n".join(fallback_lines)
    else:
        book_info = format_book_info_html_ordered(
            book_info, book_title=book_title, language=language
        )

    # For front sections with no explicit title: keep the page but leave
    # nav_title unset so EpubBuilder assigns the prefix label
    # (অন্যান্য / Others, with a digit when there are multiple) per the spec.
    # The page itself renders with no heading — the content is presented as-is.
    pruned_sections = []
    for _sec in front_sections:
        if ((_sec.get("title") or "").strip()):
            pruned_sections.append(_sec)
        elif plain_text_from_html(_sec.get("html", "")):
            # Unnamed prose — keep with no nav_title; builder handles the label.
            _sec = dict(_sec)
            _sec["title"] = ""  # ensure no heading rendered on page
            pruned_sections.append(_sec)
        # else: empty unnamed section — discard
    front_sections = pruned_sections

    # Drop inline TOC sections when we already produce a generated toc.xhtml.
    # Keeping them would show two identical "সূচিপত্র" entries in the nav.
    if toc or content_items:
        front_sections = _drop_inline_toc_front_sections(front_sections)

    # Drop front sections whose titles duplicate a lesson/chapter name from the
    # TOC.  Landing pages sometimes surface lesson headings as extractable
    # sections; the result is an empty front page that duplicates the chapter.
    if toc and front_sections:
        front_sections = _drop_chapter_title_front_sections(front_sections, toc)

    return {
        "book_info": book_info,
        "dedication": dedication,
        "front_sections": front_sections,
        "back_sections": back_sections,
        "main_content": residual_main,
        "toc": toc,
        "content_items": content_items,
    }


def projection_from_manifest_parts(
    *,
    canonical_url,
    title,
    author,
    series,
    book_type,
    cover,
    cover_source_url,
    output_folder,
    sections_payload,
):
    return {
        "book_title": title,
        "author": author,
        "series": series,
        "book_type": book_type,
        "cover": cover or cover_source_url or "",
        "cover_source_url": cover_source_url or "",
        "main_content": sections_payload["main_content"],
        "book_info": sections_payload["book_info"],
        "dedication": sections_payload["dedication"],
        "front_sections": sections_payload["front_sections"],
        "back_sections": sections_payload["back_sections"],
        "toc": sections_payload["toc"],
        "content_items": sections_payload["content_items"],
        "output_folder": output_folder,
        "source_url": canonical_url,
    }


def build_manifest_from_projection(canonical_url, projection, *, pages=None, source_structure=None, metadata=None):
    projection = dict(projection or {})
    if projection.get("content_items") and not projection.get("toc"):
        projection["toc"] = generated_toc_from_content_items(projection["content_items"])

    entities, evidences = extract_book_entities(projection, canonical_url)
    sections = extract_sections(projection, canonical_url)
    assets = [item for item in entities if item.get("entity_type") == "asset"]
    structure = source_structure or {"type": classify_structure(projection)}
    return {
        "schema_version": CURRENT_MANIFEST_SCHEMA_VERSION,
        "canonical_url": canonical_url,
        "source_url": projection.get("source_url") or canonical_url,
        "book": {
            "title": projection.get("book_title", ""),
            "author": projection.get("author", ""),
            "series": projection.get("series", ""),
            "book_type": projection.get("book_type", ""),
        },
        "metadata": metadata or {},
        "source_structure": structure,
        "projection": projection,
        "entities": entities,
        "evidence": evidences,
        "sections": sections,
        "assets": assets,
        "pages": pages or [],
    }


def build_manifest_source_pages(source_url, *, content_limits=None, page_cache=None):
    canonical_url = normalize_source_url(source_url)
    limits = normalize_manifest_limits(content_limits)
    with create_session_with_retries() as session:
        ctx = SourceFetchContext(session)
        landing_soup = ctx.fetch_soup(canonical_url, kind="landing")
        if not landing_soup:
            return {
                "schema_version": CURRENT_MANIFEST_SCHEMA_VERSION,
                "source_url": canonical_url,
                "canonical_url": canonical_url,
                "pages": ctx.pages,
                "manifest": {},
                "raw_scrape_payload": {},
            }

        title, title_author = extract_title_and_author(landing_soup)
        terms = extract_entry_terms(landing_soup)
        author = term_display(terms, "authors", "author") or title_author
        series = term_display(terms, "series")
        book_type = term_display(terms, "ld_course_category", "category")
        output_folder = scraper.create_output_folder(title)
        cover_source_url = extract_cover_url(landing_soup, canonical_url)
        cover = download_cover_asset(cover_source_url, output_folder, session)
        landing_main_content = extract_entry_content_html(landing_soup, title)

        toc_nodes, toc_meta = collect_learndash_toc(landing_soup, canonical_url, ctx, limits)
        landing_soup.decompose()
        content_items = collect_content_items(toc_nodes, ctx, limits, page_cache=page_cache) if toc_nodes else []
        sections_payload = normalize_body_sections(
            book_title=title,
            landing_main_content=landing_main_content,
            toc_nodes=toc_nodes,
            content_items=content_items,
            author=author,
            series=series,
            book_type=book_type,
        )
        source_structure = classify_manifest_structure(
            toc_nodes,
            sections_payload["content_items"],
            sections_payload["main_content"],
            toc_meta,
            limits=limits,
        )
        projection = projection_from_manifest_parts(
            canonical_url=canonical_url,
            title=title,
            author=author,
            series=series,
            book_type=book_type,
            cover=cover,
            cover_source_url=cover_source_url,
            output_folder=output_folder,
            sections_payload=sections_payload,
        )
        manifest = build_manifest_from_projection(
            canonical_url,
            projection,
            pages=ctx.pages,
            source_structure=source_structure,
            metadata={"entry_terms": terms, "title_author": title_author},
        )
        manifest["toc_source"] = toc_nodes
        return {
            "schema_version": CURRENT_MANIFEST_SCHEMA_VERSION,
            "source_url": canonical_url,
            "canonical_url": canonical_url,
            "pages": ctx.pages,
            "manifest": manifest,
            "raw_scrape_payload": projection,
        }


def build_manifest_from_legacy_payload(source_url, scraped_data):
    canonical_url = normalize_source_url(source_url)
    normalized_payload = dict(scraped_data) if isinstance(scraped_data, dict) else {}
    promoted_book_info, cleaned_main_content = promote_leading_front_matter(
        normalized_payload.get("book_info", ""),
        normalized_payload.get("main_content", ""),
    )
    normalized_payload["book_info"] = promoted_book_info
    normalized_payload["main_content"] = cleaned_main_content
    if normalized_payload.get("content_items") and not normalized_payload.get("toc"):
        normalized_payload["toc"] = generated_toc_from_content_items(normalized_payload["content_items"])
    projection = build_projection(normalized_payload, canonical_url)
    pages = [
        {
            "url": canonical_url,
            "kind": "landing",
            "title": projection.get("book_title", ""),
            "status": "fetched" if isinstance(scraped_data, dict) else "failed",
            "status_code": None,
        }
    ]
    for index, item in enumerate(projection.get("content_items", []) or []):
        source_item_url = (item or {}).get("source_url")
        if source_item_url:
            pages.append(
                {
                    "url": source_item_url,
                    "kind": (item or {}).get("type") or "content",
                    "title": (item or {}).get("title", ""),
                    "status": "fetched",
                    "status_code": None,
                    "index": index,
                }
            )
    manifest = build_manifest_from_projection(
        canonical_url,
        projection,
        pages=pages,
        source_structure={"type": classify_structure(projection), "legacy_payload": True},
    )
    return {
        "schema_version": CURRENT_MANIFEST_SCHEMA_VERSION,
        "source_url": canonical_url,
        "canonical_url": canonical_url,
        "pages": pages,
        "manifest": manifest,
        "raw_scrape_payload": projection,
    }


def manifest_to_projection(manifest):
    projection = dict((manifest or {}).get("projection") or {})
    projection.setdefault("book_title", (manifest or {}).get("book", {}).get("title", ""))
    projection.setdefault("author", (manifest or {}).get("book", {}).get("author", ""))
    projection.setdefault("series", (manifest or {}).get("book", {}).get("series", ""))
    projection.setdefault("book_type", (manifest or {}).get("book", {}).get("book_type", ""))
    projection.setdefault("cover", "")
    projection.setdefault("cover_source_url", "")
    projection.setdefault("main_content", "")
    projection.setdefault("book_info", "")
    projection.setdefault("dedication", "")
    projection.setdefault("front_sections", [])
    projection.setdefault("back_sections", [])
    projection.setdefault("toc", [])
    projection.setdefault("content_items", [])
    projection.setdefault("output_folder", "")
    projection.setdefault("source_url", (manifest or {}).get("canonical_url", ""))
    return projection

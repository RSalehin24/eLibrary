from urllib.parse import parse_qs, urlencode


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


def crawl_inline_toc_entry(
    entry,
    remaining_items,
    base_url,
    cache,
    active_urls,
    crawl_state,
    crawl_limits,
    depth,
):
    title = clean_display_text(entry.get("title", ""))
    node_type = entry.get("type") or "lesson"
    raw_url = (entry.get("url") or "").strip()
    local_content_item = consume_inline_content_item(title, remaining_items)
    local_content = truncate_scraped_content(
        clean_content_html(
            local_content_item.get("content", "") if local_content_item else "",
            title,
        ),
        crawl_limits.get("max_content_chars"),
    )

    nested_children = [
        child
        for child in (
            crawl_inline_toc_entry(
                child_entry,
                remaining_items,
                base_url,
                cache,
                active_urls,
                crawl_state,
                crawl_limits,
                depth + 1,
            )
            for child_entry in entry.get("children", []) or []
        )
        if child
    ]

    if raw_url and not raw_url.startswith("#"):
        normalized_url = normalize_crawl_url(raw_url, base_url=base_url)
        if normalized_url:
            linked_node = scrape_recursive_content_node(
                normalized_url,
                title_hint=title,
                node_type=node_type,
                cache=cache,
                active_urls=active_urls,
                crawl_state=crawl_state,
                crawl_limits=crawl_limits,
                depth=depth,
            )
            if local_content and not linked_node.get("content"):
                linked_node["content"] = local_content
            if title:
                linked_node["title"] = title
            linked_node["type"] = node_type
            linked_node["children"] = merge_unique_children(
                linked_node.get("children", []),
                nested_children,
            )
            return linked_node

    if not title and not local_content and not nested_children:
        return None

    return build_content_node(
        title,
        node_type=node_type,
        content=local_content,
        children=nested_children,
    )


def content_node_to_toc_entry(node, parent_path=()):
    title = normalize_structured_heading_title(node.get("title", ""))
    if not title:
        return None

    path = list(parent_path) + [title]
    child_entries = [
        child_entry
        for child_entry in (
            content_node_to_toc_entry(child, tuple(path))
            for child in node.get("children", [])
        )
        if child_entry
    ]
    has_content = bool(node.get("content"))
    if not has_content and not child_entries:
        return None

    entry = {
        "title": title,
        "type": node.get("type", "lesson"),
        "has_content": has_content,
        "path": path,
    }
    if child_entries:
        entry["children"] = child_entries
    return entry


def flatten_content_nodes(nodes, parent_path=(), max_items=None):
    items = []

    for node in nodes:
        title = normalize_structured_heading_title(node.get("title", ""))
        path = list(parent_path) + [title]
        if node.get("content"):
            items.append(
                {
                    "title": title,
                    "content": node["content"],
                    "type": node.get("type", "lesson"),
                    "parent": parent_path[-1] if parent_path else None,
                    "path": path,
                }
            )
            if isinstance(max_items, int) and max_items > 0 and len(items) >= max_items:
                return items

        child_limit = None
        if isinstance(max_items, int) and max_items > 0:
            child_limit = max_items - len(items)
            if child_limit <= 0:
                return items

        items.extend(
            flatten_content_nodes(
                node.get("children", []),
                tuple(path),
                max_items=child_limit,
            )
        )

        if isinstance(max_items, int) and max_items > 0 and len(items) >= max_items:
            return items

    return items


def get_total_pages(soup):
    pager = soup.find("div", class_="ld-pagination ld-pagination-page-course_content_shortcode")
    if pager and pager.has_attr("data-pager-results"):
        try:
            data = json.loads(pager["data-pager-results"].replace("&quot;", '"'))
            return int(data.get("total_pages", 1))
        except Exception:
            pass
    return 1


def find_expanded_topic_container(lesson_item, expand_id):
    if not expand_id:
        return None
    return lesson_item.find("div", id=f"{expand_id}-container")


def find_lesson_item_by_expand_id(soup, expand_id):
    return soup.find("div", attrs={"data-ld-expand-id": expand_id})


def extract_topic_entries(lesson_item, seen_urls, base_url=""):
    expand_id = lesson_item.get("data-ld-expand-id")
    expanded_container = find_expanded_topic_container(lesson_item, expand_id)
    if expanded_container is None:
        return []

    topics = []
    topic_items = expanded_container.find_all(
        "div",
        class_=lambda c: c and "ld-table-list-item" in c,
        recursive=True,
    )

    for topic_item in topic_items:
        anchor = topic_item.find(
            "a",
            class_=lambda c: c and "ld-table-list-item-preview" in c,
        )
        if anchor is None or not anchor.get("href"):
            continue

        normalized_url = normalize_crawl_url(anchor["href"], base_url=base_url)
        topic_key = normalized_url or anchor["href"]
        if topic_key in seen_urls:
            continue
        seen_urls.add(topic_key)

        title_span = anchor.find("span", class_="ld-topic-title")
        title = (
            normalize_structured_heading_title(title_span.get_text(" ", strip=True))
            if title_span is not None
            else normalize_structured_heading_title(anchor.get_text(" ", strip=True))
        )
        if not title:
            continue
        topics.append((title, normalized_url or anchor["href"]))

    return topics


def topic_page_numbers(lesson_item, page_url, expand_id, max_topic_pages=None):
    page_numbers = {1}
    if not expand_id:
        return [1]

    for tag in lesson_item.find_all(href=True):
        parsed = urlparse(urljoin(page_url, tag.get("href", "")))
        for value in parse_qs(parsed.query).get("ld-topic-page", []):
            prefix, _, page_number = str(value).partition("-")
            if prefix != str(expand_id):
                continue
            try:
                page_numbers.add(int(page_number))
            except (TypeError, ValueError):
                continue

    for tag in lesson_item.find_all(attrs={"data-ld-topic-page": True}):
        prefix, _, page_number = str(tag.get("data-ld-topic-page", "")).partition("-")
        if prefix != str(expand_id):
            continue
        try:
            page_numbers.add(int(page_number))
        except (TypeError, ValueError):
            continue

    pagination = lesson_item.find(
        "div",
        class_=lambda c: c and "ld-pagination" in c,
    )
    if pagination and pagination.has_attr("data-pager-results"):
        try:
            data = json.loads(pagination["data-pager-results"].replace("&quot;", '"'))
            total_pages = int(data.get("total_pages", 1))
            upper_bound = total_pages
            if isinstance(max_topic_pages, int) and max_topic_pages > 0:
                upper_bound = min(upper_bound, max_topic_pages)
            page_numbers.update(range(1, upper_bound + 1))
        except Exception:
            pass

    numbers = sorted(page_number for page_number in page_numbers if page_number >= 1)
    if isinstance(max_topic_pages, int) and max_topic_pages > 0:
        numbers = [page_number for page_number in numbers if page_number <= max_topic_pages]
    return numbers or [1]


def scrape_nested_topics(lesson_item, page_url="", max_topic_pages=None):
    """
    Recursively scrape topics from a lesson item's expanded content, including
    paginated topic lists like ld-topic-page=<expand_id>-<page>.
    """
    topics = []
    seen_urls = set()

    expand_id = lesson_item.get("data-ld-expand-id")
    if not expand_id:
        return topics

    for page_number in topic_page_numbers(
        lesson_item,
        page_url,
        expand_id,
        max_topic_pages=max_topic_pages,
    ):
        if page_number == 1:
            paged_lesson_item = lesson_item
        else:
            topic_page_url = build_query_url(
                page_url,
                {"ld-topic-page": f"{expand_id}-{page_number}"},
            )
            topic_soup = get_soup(topic_page_url)
            if not topic_soup:
                continue
            paged_lesson_item = find_lesson_item_by_expand_id(topic_soup, expand_id)
            if paged_lesson_item is None:
                continue

        topics.extend(
            extract_topic_entries(
                paged_lesson_item,
                seen_urls,
                base_url=topic_page_url if page_number > 1 else page_url,
            )
        )

    return topics


def scrape_lesson_list(soup, page_url="", max_topic_pages=None):
    """
    Scrape lessons and their nested topics from the page.
    Returns a list of dictionaries with lesson info and nested topics.
    """
    lessons = []

    lesson_items = soup.find_all(
        "div",
        class_=lambda c: c and "ld-item-lesson-item" in c,
    )

    for lesson_item in lesson_items:
        anchor = lesson_item.find("a", class_="ld-item-name")
        if anchor is None:
            continue

        title_div = anchor.find("div", class_="ld-item-title")
        if title_div is None:
            continue

        lesson_title = title_div.get_text(" ", strip=True)
        lesson_title = re.sub(r"\d+\s*Topics.*$", "", lesson_title, flags=re.IGNORECASE)
        lesson_title = normalize_structured_heading_title(lesson_title)
        lesson_url = anchor.get("href")
        topics = scrape_nested_topics(
            lesson_item,
            page_url=page_url,
            max_topic_pages=max_topic_pages,
        )

        lessons.append(
            {
                "title": lesson_title,
                "url": lesson_url,
                "topics": topics,
                "has_topics": len(topics) > 0,
                "listing_url": page_url,
            }
        )

    return lessons


def scrape_all_lessons(book_url, max_pages=None, max_topic_pages=None):
    """
    Scrape all lessons across all pages.
    Returns a list of lesson dictionaries.
    """
    lessons = []
    seen_lessons = set()
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            break

        page_url = build_query_url(book_url, {"ld-courseinfo-lesson-page": page})
        soup = get_soup(page_url)
        if not soup:
            break

        try:
            page_lessons = scrape_lesson_list(
                soup,
                page_url=page_url,
                max_topic_pages=max_topic_pages,
            )
        except TypeError:
            page_lessons = scrape_lesson_list(soup)

        for lesson in page_lessons:
            lesson_key = (
                normalize_text(lesson.get("url") or ""),
                normalize_text(lesson.get("title") or ""),
            )
            if lesson_key in seen_lessons:
                continue
            seen_lessons.add(lesson_key)
            lessons.append(lesson)
        if page >= get_total_pages(soup):
            break

        page += 1
        time.sleep(1)

    return lessons

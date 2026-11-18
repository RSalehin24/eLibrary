

def clean_content_html(html_content, title=""):
    if not html_content:
        return ""

    cleaned = remove_redundant_headers(html_content, title).strip()
    text_content = clean_display_text(
        BeautifulSoup(cleaned, "html.parser").get_text(" ", strip=True)
    )
    if not text_content:
        return ""
    return cleaned


def build_content_node(title, node_type="lesson", content="", children=None):
    return {
        "title": normalize_structured_heading_title(title or ""),
        "type": node_type or "lesson",
        "content": content or "",
        "children": list(children or []),
    }


def is_direct_book_root_url(url):
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    return len(path_parts) == 2 and path_parts[0] == "books"


def consume_inline_content_item(title, remaining_items):
    if not title:
        return None

    for index, item in enumerate(remaining_items):
        if texts_are_similar(item.get("title", ""), title):
            return remaining_items.pop(index)

    return None


def merge_unique_children(existing_children, incoming_children):
    merged = list(existing_children or [])
    seen = {
        (normalize_text(child.get("title", "")), child.get("type", "lesson"))
        for child in merged
    }

    for child in incoming_children or []:
        key = (normalize_text(child.get("title", "")), child.get("type", "lesson"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(child)

    return merged


def scrape_recursive_content_node(
    url,
    title_hint="",
    node_type="lesson",
    cache=None,
    active_urls=None,
    prefetched_soup=None,
    prefetched_main_content=None,
    crawl_state=None,
    crawl_limits=None,
    depth=0,
):
    cache = cache if cache is not None else {}
    active_urls = active_urls if active_urls is not None else set()
    crawl_state = crawl_state if isinstance(crawl_state, dict) else {"visited_nodes": 0}
    crawl_limits = (
        crawl_limits if isinstance(crawl_limits, dict) else normalize_scrape_limits()
    )
    normalized_url = normalize_crawl_url(url)

    if not normalized_url:
        return build_content_node(title_hint, node_type=node_type)

    if depth > crawl_limits["max_depth"]:
        return build_content_node(title_hint or normalized_url, node_type=node_type)

    if crawl_state.get("visited_nodes", 0) >= crawl_limits["max_nodes"]:
        return build_content_node(title_hint or normalized_url, node_type=node_type)

    if prefetched_soup is None and prefetched_main_content is None and normalized_url in cache:
        cached_node = cache[normalized_url]
        return {
            "title": normalize_structured_heading_title(title_hint) or cached_node.get("title", ""),
            "type": node_type or cached_node.get("type", "lesson"),
            "content": cached_node.get("content", ""),
            "children": cached_node.get("children", []),
        }

    if normalized_url in active_urls:
        return build_content_node(title_hint or normalized_url, node_type=node_type)

    crawl_state["visited_nodes"] = crawl_state.get("visited_nodes", 0) + 1
    active_urls.add(normalized_url)

    try:
        soup = prefetched_soup or get_soup(normalized_url)
        if not soup:
            node = build_content_node(title_hint or normalized_url, node_type=node_type)
            cache[normalized_url] = node
            return node

        page_title, _ = extract_title_and_author(soup)
        resolved_title = normalize_structured_heading_title(
            title_hint or page_title or normalized_url
        )
        main_content = (
            prefetched_main_content
            if prefetched_main_content is not None
            else scrape_main_content(soup)
        )

        if prefetched_main_content is None:
            _, _, main_content = extract_main_content_segments(main_content)

        children = []
        cleaned_page_content = truncate_scraped_content(
            clean_content_html(main_content, resolved_title),
            crawl_limits.get("max_content_chars"),
        )

        if (
            urlparse(normalized_url).path.startswith("/books/")
            and (node_type == "book" or is_direct_book_root_url(normalized_url))
        ):
            lessons = scrape_all_lessons(
                normalized_url,
                max_pages=crawl_limits.get("max_lesson_pages"),
                max_topic_pages=crawl_limits.get("max_lesson_pages"),
            )
            if lessons:
                for lesson_data in lessons:
                    lesson_url = normalize_crawl_url(
                        lesson_data.get("url", ""),
                        base_url=lesson_data.get("listing_url") or normalized_url,
                    ) or lesson_data.get("url", "")
                    if lesson_data["has_topics"]:
                        topic_children = []
                        for topic_title, topic_url in lesson_data["topics"]:
                            topic_children.append(
                                scrape_recursive_content_node(
                                    topic_url,
                                    title_hint=topic_title,
                                    node_type="topic",
                                    cache=cache,
                                    active_urls=active_urls,
                                    crawl_state=crawl_state,
                                    crawl_limits=crawl_limits,
                                    depth=depth + 1,
                                )
                            )
                        lesson_node = (
                            scrape_recursive_content_node(
                                lesson_url,
                                title_hint=lesson_data["title"],
                                node_type="lesson",
                                cache=cache,
                                active_urls=active_urls,
                                crawl_state=crawl_state,
                                crawl_limits=crawl_limits,
                                depth=depth + 1,
                            )
                            if lesson_url
                            else build_content_node(
                                lesson_data["title"],
                                node_type="lesson",
                            )
                        )
                        lesson_node["title"] = normalize_structured_heading_title(
                            lesson_data["title"]
                        )
                        lesson_node["type"] = "lesson"
                        lesson_node["children"] = merge_unique_children(
                            lesson_node.get("children", []),
                            topic_children,
                        )
                        children.append(lesson_node)
                    else:
                        children.append(
                            scrape_recursive_content_node(
                                lesson_url,
                                title_hint=lesson_data["title"],
                                node_type="lesson",
                                cache=cache,
                                active_urls=active_urls,
                                crawl_state=crawl_state,
                                crawl_limits=crawl_limits,
                                depth=depth + 1,
                            )
                        )

        if not children:
            inline_toc, inline_content_items, cleaned_main_content = extract_inline_toc_and_content(
                main_content
            )
            if inline_toc:
                remaining_inline_items = [dict(item) for item in inline_content_items]
                children = [
                    child
                    for child in (
                        crawl_inline_toc_entry(
                            entry,
                            remaining_inline_items,
                            normalized_url,
                            cache,
                            active_urls,
                            crawl_state,
                            crawl_limits,
                            depth + 1,
                        )
                        for entry in inline_toc
                    )
                    if child
                ]
                cleaned_page_content = truncate_scraped_content(
                    clean_content_html(cleaned_main_content, resolved_title),
                    crawl_limits.get("max_content_chars"),
                )

        node = build_content_node(
            resolved_title,
            node_type=node_type,
            content=cleaned_page_content,
            children=children,
        )
        cache[normalized_url] = node
        return node
    finally:
        active_urls.discard(normalized_url)

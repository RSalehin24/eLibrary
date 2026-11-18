
from apps.ingestion.services.normalization import (
    dedupe_html_fragment_blocks,
    dedupe_structured_sections,
    extract_boundary_sections_from_content_items,
    infer_structured_content_from_main_content,
    prune_duplicate_main_content,
    split_leading_front_sections,
    split_trailing_front_sections,
)


def scrape_lesson_content(url, title=""):
    """Scrape content from a lesson or topic URL."""
    soup = get_soup(url)
    if not soup:
        return ""

    container = (
        soup.select_one(".ld-tab-content.ld-visible.entry-content")
        or soup.select_one(".ld-tab-content.entry-content")
        or soup.select_one("article .entry-content")
        or soup.select_one(".entry-content")
    )
    if container:
        container = clean_buttons(container)
        content = container.decode_contents()
        content = remove_redundant_headers(content, title)
        return content
    return ""

def build_toc_structure(lessons_data):
    """
    Build a hierarchical table of contents structure.
    Returns a list representing the TOC.
    """
    toc = []
    
    for lesson in lessons_data:
        lesson_entry = {
            "title": lesson["title"],
            "type": "lesson",
            "has_content": True
        }
        
        if lesson["has_topics"]:
            # This lesson has topics
            lesson_entry["children"] = []
            for topic_title, topic_url in lesson["topics"]:
                lesson_entry["children"].append({
                    "title": topic_title,
                    "type": "topic",
                    "has_content": True
                })
        
        toc.append(lesson_entry)
    
    return toc

def scrape_book_data(book_url, *, content_limits=None):
    book_url = normalize_source_url(book_url)
    soup = get_soup(book_url)
    if not soup:
        print("Failed to fetch the book page.")
        return None

    book_title, title_author = extract_title_and_author(soup)
    meta_author, series, book_type = scrape_book_meta(soup)
    author = meta_author or title_author
    output_folder = create_output_folder(book_title)

    cover = download_cover_image(soup, output_folder)
    main_content = scrape_main_content(soup)

    # Extract book info and dedication from main content
    book_info, dedication, main_content = extract_dedication(main_content)
    book_info = dedupe_html_fragment_blocks(book_info)
    dedication = dedupe_html_fragment_blocks(dedication)

    crawl_limits = normalize_scrape_limits(content_limits)
    disable_recursive = False
    if isinstance(content_limits, dict):
        raw_disable_recursive = content_limits.get("disable_recursive", False)
        if isinstance(raw_disable_recursive, str):
            disable_recursive = raw_disable_recursive.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        else:
            disable_recursive = bool(raw_disable_recursive)

    if disable_recursive:
        print("Skipping recursive content structure fetch.")
        toc = []
        content_items = []
        main_content = truncate_scraped_content(
            main_content,
            crawl_limits.get("max_content_chars"),
        )
    else:
        print("Fetching recursive content structure...")
        root_node = scrape_recursive_content_node(
            book_url,
            title_hint=book_title,
            node_type="book",
            cache={},
            active_urls=set(),
            prefetched_soup=soup,
            prefetched_main_content=main_content,
            crawl_state={"visited_nodes": 0},
            crawl_limits=crawl_limits,
            depth=0,
        )
        toc = [
            toc_entry
            for toc_entry in (
                content_node_to_toc_entry(child)
                for child in root_node.get("children", [])
            )
            if toc_entry
        ]
        content_items = flatten_content_nodes(
            root_node.get("children", []),
            max_items=crawl_limits.get("max_nodes"),
        )
        main_content = root_node.get("content", main_content)

    front_sections = []
    back_sections = []

    # Trust the source's explicit body structure (TOC or content_items) when
    # available: never strip from inside lessons and never re-mine landing
    # main_content as back-matter (that residual is already front-matter).
    has_explicit_body = bool(toc or content_items)

    extracted_front_sections, main_content = split_leading_front_sections(
        main_content or "",
        has_explicit_body=has_explicit_body,
    )
    if extracted_front_sections:
        front_sections.extend(extracted_front_sections)

    if not toc and not content_items:
        inferred_toc, inferred_content_items, main_content = infer_structured_content_from_main_content(
            main_content,
            book_title=book_title,
        )
        if inferred_toc and inferred_content_items:
            toc = inferred_toc
            content_items = inferred_content_items

    if content_items:
        (
            inferred_front_sections,
            inferred_back_sections,
            toc,
            content_items,
        ) = extract_boundary_sections_from_content_items(
            content_items,
            toc,
            trust_source_toc=has_explicit_body,
        )
        front_sections.extend(inferred_front_sections)
        back_sections.extend(inferred_back_sections)

    if not has_explicit_body:
        extracted_back_sections, main_content = split_trailing_front_sections(main_content or "")
        if extracted_back_sections:
            back_sections.extend(extracted_back_sections)

    front_sections = dedupe_structured_sections(
        front_sections,
        reference_fragments=[book_info, dedication],
    )
    back_sections = dedupe_structured_sections(
        back_sections,
        reference_fragments=[book_info, dedication],
    )
    main_content = prune_duplicate_main_content(
        main_content,
        reference_fragments=[
            book_info,
            dedication,
            *[section.get("html", "") for section in front_sections],
            *[section.get("html", "") for section in back_sections],
        ],
        content_items=content_items,
    )

    return {
        "book_title": book_title,
        "author": author,
        "series": series,
        "book_type": book_type,
        "cover": cover,
        "main_content": main_content,
        "book_info": book_info,  # Extracted book info before dedication
        "dedication": dedication,  # Extracted dedication
        "front_sections": front_sections,
        "back_sections": back_sections,
        "toc": toc,
        "content_items": content_items,
        "output_folder": output_folder
    }

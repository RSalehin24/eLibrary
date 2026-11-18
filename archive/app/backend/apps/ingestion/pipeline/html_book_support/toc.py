import base64
import mimetypes
import os
import re
from html import escape


def display_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("display_name", "name", "title"):
            if value.get(key):
                return str(value[key])
        return ", ".join(display_value(item) for item in value.values() if item)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(display_value(item) for item in value if item)
    return str(value)


def make_unique_id(name, existing):
    """Generate a unique anchor id for HTML headings."""
    slug = re.sub(r"\W+", "_", name.lower().strip())
    base = slug
    index = 1
    while slug in existing:
        slug = f"{base}_{index}"
        index += 1
    existing.add(slug)
    return slug


def resolve_cover_path(cover, output_folder):
    if cover and str(cover).startswith(("http://", "https://", "data:")):
        return str(cover)

    if not output_folder or not os.path.isdir(output_folder):
        return ""

    if cover:
        direct_path = cover if os.path.isabs(cover) else os.path.join(output_folder, cover)
        if os.path.exists(direct_path):
            return direct_path

        requested_base = os.path.splitext(os.path.basename(str(cover)))[0]
        if requested_base:
            for filename in sorted(os.listdir(output_folder)):
                if os.path.splitext(filename)[0] == requested_base:
                    candidate_path = os.path.join(output_folder, filename)
                    if os.path.isfile(candidate_path):
                        return candidate_path

    for filename in sorted(os.listdir(output_folder)):
        if os.path.splitext(filename)[0] == "book_cover":
            candidate_path = os.path.join(output_folder, filename)
            if os.path.isfile(candidate_path):
                return candidate_path

    return ""


def html_cover_source(cover, output_folder):
    cover_path = resolve_cover_path(cover, output_folder)
    if not cover_path:
        return ""
    if cover_path.startswith(("http://", "https://", "data:")):
        return cover_path

    mime_type = mimetypes.guess_type(cover_path)[0] or "image/jpeg"
    with open(cover_path, "rb") as handle:
        encoded_image = base64.b64encode(handle.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded_image}"


def content_path_tuple(path_value):
    if isinstance(path_value, (list, tuple)):
        return tuple(part for part in path_value if part)
    return ()


def resolve_entry_path(entry, parent_path=()):
    explicit_path = content_path_tuple(entry.get("path"))
    if explicit_path:
        return explicit_path
    return tuple(parent_path) + (entry.get("title", ""),)


def build_toc_id_map(toc, existing_ids, parent_path=()):
    id_map = {}

    for entry in toc:
        path = resolve_entry_path(entry, parent_path)
        seed = "__".join(path) or entry.get("title", "section")
        id_map[path] = make_unique_id(seed, existing_ids)
        if entry.get("children"):
            id_map.update(build_toc_id_map(entry["children"], existing_ids, path))

    return id_map


def build_hierarchical_toc_html(toc, id_map, parent_path=(), level=0):
    html = ""

    for entry in toc:
        path = resolve_entry_path(entry, parent_path)
        anchor_id = id_map.get(path, "")
        title = escape(entry.get("title", ""))
        has_children = bool(entry.get("children"))
        has_content = entry.get("has_content", False)
        title_markup = (
            f"<a href='#{anchor_id}'>{title}</a>"
            if anchor_id and (has_content or not has_children)
            else f"<strong>{title}</strong>"
        )
        item_class = "toc-lesson" if level == 0 else "toc-topic"

        html += f"\n          <li class='{item_class}'>"
        html += f"\n            {title_markup}"
        if has_children:
            html += "\n            <ul class='toc-topics'>"
            html += build_hierarchical_toc_html(entry["children"], id_map, path, level + 1)
            html += "\n            </ul>"
        html += "\n          </li>"

    return html


def find_content_item(entry, parent_path, content_items):
    expected_path = resolve_entry_path(entry, parent_path)

    for item in content_items:
        if content_path_tuple(item.get("path")) == expected_path:
            return item

    parent_title = parent_path[-1] if parent_path else None
    for item in content_items:
        if item.get("title") != entry.get("title"):
            continue
        if item.get("parent") == parent_title:
            return item
        if parent_title is None and not item.get("parent"):
            return item

    return None


def heading_tag_for_level(level):
    return f"h{min(6, level + 2)}"


def render_content_entry(entry, content_items, id_map, parent_path=(), level=0):
    path = resolve_entry_path(entry, parent_path)
    entry_id = id_map.get(path, "")
    content_item = find_content_item(entry, parent_path, content_items)
    children = entry.get("children", [])

    if not content_item and not children:
        return ""

    heading_tag = heading_tag_for_level(level)
    container_class = "lesson-section" if level == 0 else "topic-section"
    header_class = "lesson-header" if level == 0 else "topic-header"
    content_class = "lesson-content" if level == 0 else "topic-content"
    id_attr = f" id='{entry_id}'" if entry_id else ""
    html = f"\n    <div class='{container_class}'>"
    if level == 0:
        html += "\n      <hr class='lesson-divider'>"
    html += (
        f"\n      <{heading_tag} class='{header_class}'"
        f"{id_attr}>"
        f"{escape(entry.get('title', ''))}</{heading_tag}>"
    )

    if content_item and content_item.get("content"):
        html += f"\n      <div class='{content_class}'>"
        indented = "\n".join(
            f"        {line}" for line in content_item["content"].splitlines()
        )
        html += f"\n{indented}"
        html += "\n      </div>"

    for child in children:
        html += render_content_entry(child, content_items, id_map, path, level + 1)

    html += "\n    </div>"
    return html


def generate_content_html(content_items, toc, id_map):
    return "".join(
        render_content_entry(entry, content_items, id_map) for entry in toc
    )

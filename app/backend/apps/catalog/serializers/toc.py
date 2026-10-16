def collect_empty_toc_nodes(nodes):
    """Recursively collect non-section TOC entries with no content."""
    result = []
    for node in nodes or []:
        node_type = node.get("type", "lesson")
        if node_type != "section" and node.get("has_content") is not True:
            result.append({
                "title": node.get("title", ""),
                "type": node_type,
                "has_content": node.get("has_content"),  # False or None
                "source_url": node.get("source_url", ""),
                "path": node.get("path", []),
            })
        result.extend(
            collect_empty_toc_nodes(node.get("children", []))
        )
    return result


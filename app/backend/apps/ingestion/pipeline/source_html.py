import re
from html import escape

from apps.ingestion.services.normalization import plain_text_from_html

INVALID_XML_CONTROLS = r"[\x00-\x08\x0b\x0c\x0e-\x1f]"
BROKEN_NUMERIC_ENTITY = re.compile(INVALID_XML_CONTROLS + r"#(\d+|[xX][0-9a-fA-F]+);")


def repair_source_html(value):
    # Some source pages contain a control byte where an entity's ampersand belongs.
    repaired = BROKEN_NUMERIC_ENTITY.sub(r"&#\1;", value)
    return re.sub(INVALID_XML_CONTROLS, "", repaired)


def preserve_single_flow_body(sections):
    if (
        sections["toc"]
        or sections["content_items"]
        or plain_text_from_html(sections["main_content"])
    ):
        return sections
    fragments = [
        f"<h2>{escape(part.get('title', ''))}</h2>{part['html']}"
        for part in [*sections["front_sections"], *sections["back_sections"]]
        if plain_text_from_html(part.get("html", ""))
    ]
    if not fragments:
        return sections
    # An introductory heading must not make the entire available book disappear.
    return {
        **sections,
        "main_content": "\n".join(fragments),
        "front_sections": [],
        "back_sections": [],
    }

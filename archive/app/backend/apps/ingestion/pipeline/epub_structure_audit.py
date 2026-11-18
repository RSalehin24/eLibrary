"""
Pure EPUB structural auditor used by the 300-book regression harness
(``tests/scripts/regression_curate_300.sh``).

Given a finished ``.epub`` produced by :func:`apps.ingestion.pipeline.epub_book.create_epub`,
verify that:

* spine order is ``cover → title → info? → dedication? → front_sections*
  → toc → (content+ | main_content) → back_sections* → nav`` (each optional
  category may be absent, but their relative ordering must hold);
* every content/back document has at least some visible text (no blank pages);
* the EPUB-3 navigation document (``nav.xhtml``) is comprehensive — it
  references every readable page in the book (cover, title, info,
  dedication, front sections, the printed TOC page, every content page,
  and every back section);
* the printed ``toc.xhtml`` is content-scoped — it references content
  pages (and optionally back sections) only, never front matter and
  never the nav document itself;
* the navigation document does not link to itself.

The auditor is intentionally dependency-light — it relies on ``zipfile``,
``xml.etree.ElementTree`` and a couple of regular expressions so it can run
inside the harness without re-importing the heavy ingestion stack.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree as ET


# Filename → structural slot. ``front_section_*`` / ``back_section_*`` /
# ``lesson_*`` are handled separately via regex.
_KNOWN_SLOTS = {
    "cover_page.xhtml": "cover",
    "title.xhtml": "title",
    "info.xhtml": "info",
    "dedication.xhtml": "dedication",
    "toc.xhtml": "toc",
    "main_content.xhtml": "content",
    "nav.xhtml": "nav",
}

_FRONT_RE = re.compile(r"^front_section_\d+\.xhtml$")
_BACK_RE = re.compile(r"^back_section_\d+\.xhtml$")
_LESSON_RE = re.compile(r"^lesson_\d+\.xhtml$")

# Expected slot ordering. A spine that visits these slots strictly in
# this order — with arbitrary repetitions of front/content/back — passes.
_SLOT_ORDER = [
    "cover",
    "title",
    "info",
    "dedication",
    "front",
    "toc",
    "content",
    "back",
    "nav",
]
_SLOT_RANK = {slot: idx for idx, slot in enumerate(_SLOT_ORDER)}

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_ENTITIES = ("&nbsp;", "&#160;", "&#xa0;", "&zwnj;", "&#8204;", "&#x200c;")


@dataclass
class EpubAuditResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    spine_files: List[str] = field(default_factory=list)
    spine_slots: List[str] = field(default_factory=list)
    nav_hrefs: List[str] = field(default_factory=list)
    toc_hrefs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "spine_files": list(self.spine_files),
            "spine_slots": list(self.spine_slots),
            "nav_hrefs": list(self.nav_hrefs),
            "toc_hrefs": list(self.toc_hrefs),
        }


def _classify_slot(file_name: str) -> Optional[str]:
    base = file_name.rsplit("/", 1)[-1]
    if base in _KNOWN_SLOTS:
        return _KNOWN_SLOTS[base]
    if _FRONT_RE.match(base):
        return "front"
    if _BACK_RE.match(base):
        return "back"
    if _LESSON_RE.match(base):
        return "content"
    return None


def _strip_html(html: str) -> str:
    text = html
    for entity in _WHITESPACE_ENTITIES:
        text = text.replace(entity, " ")
    text = _TAG_RE.sub(" ", text)
    return text.strip()


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _parse_opf(archive: zipfile.ZipFile) -> tuple[str, ET.Element]:
    """Locate the OPF document and return ``(opf_dir, root_element)``."""
    container_xml = archive.read("META-INF/container.xml")
    container_root = ET.fromstring(container_xml)
    rootfile = None
    for element in container_root.iter():
        if _localname(element.tag) == "rootfile":
            rootfile = element.get("full-path")
            break
    if not rootfile:
        raise ValueError("META-INF/container.xml has no rootfile entry")
    opf_root = ET.fromstring(archive.read(rootfile))
    opf_dir = ""
    if "/" in rootfile:
        opf_dir = rootfile.rsplit("/", 1)[0] + "/"
    return opf_dir, opf_root


def _build_manifest(opf_root: ET.Element) -> dict[str, str]:
    """item id → href."""
    manifest: dict[str, str] = {}
    for element in opf_root.iter():
        if _localname(element.tag) == "item":
            item_id = element.get("id")
            href = element.get("href")
            if item_id and href:
                manifest[item_id] = href
    return manifest


def _spine_idrefs(opf_root: ET.Element) -> List[tuple[str, str]]:
    """List of ``(idref, linear)`` in document order."""
    spine_entries: List[tuple[str, str]] = []
    for element in opf_root.iter():
        if _localname(element.tag) == "itemref":
            idref = element.get("idref")
            if idref:
                spine_entries.append((idref, element.get("linear", "yes")))
    return spine_entries


def _extract_nav_hrefs(nav_html: str) -> List[str]:
    """Pull ordered hrefs from the EPUB-3 nav document's primary <nav> list."""
    try:
        root = ET.fromstring(nav_html)
    except ET.ParseError:
        return []
    # Find the toc nav (epub:type="toc") if available, else the first <nav>.
    primary = None
    for element in root.iter():
        if _localname(element.tag) == "nav":
            epub_type = None
            for attr_name, attr_value in element.attrib.items():
                if _localname(attr_name) == "type" and attr_value == "toc":
                    epub_type = "toc"
                    break
            if epub_type == "toc":
                primary = element
                break
            if primary is None:
                primary = element
    if primary is None:
        return []
    hrefs: List[str] = []
    for element in primary.iter():
        if _localname(element.tag) == "a":
            href = element.get("href")
            if href:
                hrefs.append(href.split("#", 1)[0])
    return hrefs


def _extract_toc_hrefs(toc_html: str) -> List[str]:
    """Pull ordered hrefs from the printed toc.xhtml body."""
    # toc.xhtml is rendered from a Jinja template and may not be XML-parseable
    # in pathological cases (unescaped entities in titles). Use a tolerant
    # regex fallback.
    try:
        root = ET.fromstring(toc_html)
        hrefs = [
            (element.get("href") or "").split("#", 1)[0]
            for element in root.iter()
            if _localname(element.tag) == "a" and element.get("href")
        ]
        return [href for href in hrefs if href]
    except ET.ParseError:
        return [
            match.split("#", 1)[0]
            for match in re.findall(r'href="([^"]+)"', toc_html)
            if match
        ]


def audit_epub_structure(epub_path) -> EpubAuditResult:
    """Run all structural checks on the EPUB at ``epub_path``.

    Returns an :class:`EpubAuditResult`. ``ok`` is ``False`` if any check
    failed; the offending messages are appended to ``errors``.
    """
    path = Path(epub_path)
    result = EpubAuditResult(ok=True)
    if not path.exists():
        result.ok = False
        result.errors.append(f"epub file does not exist: {path}")
        return result

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        result.ok = False
        result.errors.append(f"epub is not a valid zip: {exc}")
        return result

    with archive:
        try:
            opf_dir, opf_root = _parse_opf(archive)
        except (KeyError, ET.ParseError, ValueError) as exc:
            result.ok = False
            result.errors.append(f"could not parse OPF: {exc}")
            return result

        manifest = _build_manifest(opf_root)
        spine_entries = _spine_idrefs(opf_root)

        spine_files: List[str] = []
        spine_slots: List[str] = []
        for idref, _linear in spine_entries:
            href = manifest.get(idref)
            if not href:
                result.errors.append(f"spine references unknown manifest id: {idref}")
                continue
            spine_files.append(href)
            slot = _classify_slot(href)
            if slot is None:
                result.errors.append(f"unrecognised spine file: {href}")
                slot = "unknown"
            spine_slots.append(slot)
        result.spine_files = spine_files
        result.spine_slots = spine_slots

        # Structural order: each slot rank must be monotonically
        # non-decreasing (front/content/back may repeat, but a back page
        # must not appear before a content/toc page, etc.).
        previous_rank = -1
        previous_slot = None
        for index, slot in enumerate(spine_slots):
            if slot == "unknown":
                continue
            rank = _SLOT_RANK[slot]
            if rank < previous_rank:
                result.errors.append(
                    f"spine slot out of order at position {index}: "
                    f"{previous_slot!r} → {slot!r} ({spine_files[index]})"
                )
            previous_rank = max(previous_rank, rank)
            previous_slot = slot

        # Exactly one cover/title/toc/nav and one optional info/dedication.
        for required in ("cover", "title"):
            if spine_slots.count(required) == 0:
                result.errors.append(f"missing required {required} page")
        for unique_slot in ("info", "dedication", "toc", "nav"):
            if spine_slots.count(unique_slot) > 1:
                result.errors.append(
                    f"{unique_slot!r} page appears {spine_slots.count(unique_slot)} times in spine"
                )

        # Must contain at least one content page (or a main_content fallback,
        # which classifies as 'content' too).
        if "content" not in spine_slots:
            result.errors.append("spine has no content pages")

        # Blank-page check for content + back pages.
        for href, slot in zip(spine_files, spine_slots):
            if slot not in ("content", "back", "front"):
                continue
            try:
                raw = archive.read(opf_dir + href).decode("utf-8", errors="ignore")
            except KeyError:
                result.errors.append(f"spine document missing from archive: {href}")
                continue
            if not _strip_html(raw):
                result.errors.append(f"blank {slot} page: {href}")

        # nav / toc parity + no nav self-link.
        nav_href = next(
            (href for href, slot in zip(spine_files, spine_slots) if slot == "nav"),
            None,
        )
        toc_href = next(
            (href for href, slot in zip(spine_files, spine_slots) if slot == "toc"),
            None,
        )
        if nav_href:
            try:
                nav_html = archive.read(opf_dir + nav_href).decode("utf-8", errors="ignore")
            except KeyError:
                result.errors.append(f"nav document missing from archive: {nav_href}")
            else:
                nav_hrefs = _extract_nav_hrefs(nav_html)
                result.nav_hrefs = nav_hrefs
                nav_base = nav_href.rsplit("/", 1)[-1]
                for href in nav_hrefs:
                    if href.rsplit("/", 1)[-1] == nav_base:
                        result.errors.append(f"nav document links to itself: {href}")
                        break
        if toc_href:
            try:
                toc_html = archive.read(opf_dir + toc_href).decode("utf-8", errors="ignore")
            except KeyError:
                result.errors.append(f"toc document missing from archive: {toc_href}")
            else:
                result.toc_hrefs = _extract_toc_hrefs(toc_html)

        if result.nav_hrefs and spine_files:
            # nav.xhtml must be comprehensive: every spine page except nav
            # itself should appear as a nav target. Order is checked loosely
            # (set equality) since nav nests content chapters and may
            # reorder siblings under section headers; spine order is
            # already verified above via _SLOT_RANK.
            nav_basenames = {href.rsplit("/", 1)[-1] for href in result.nav_hrefs}
            nav_basename = nav_href.rsplit("/", 1)[-1] if nav_href else ""
            expected_basenames = {
                href.rsplit("/", 1)[-1]
                for href, slot in zip(spine_files, spine_slots)
                if slot != "nav"
            }
            missing_from_nav = expected_basenames - nav_basenames
            if missing_from_nav:
                result.errors.append(
                    f"nav document is missing entries for: {sorted(missing_from_nav)!r}"
                )
            stray_in_nav = nav_basenames - expected_basenames - {nav_basename}
            if stray_in_nav:
                result.errors.append(
                    f"nav document links to non-spine files: {sorted(stray_in_nav)!r}"
                )

        if result.toc_hrefs and spine_files:
            # toc.xhtml is content-scoped: only content (lesson_*/main_content)
            # and back_section_* targets are allowed. Front matter, the toc
            # page itself, and the nav document must not appear.
            allowed_toc_basenames = {
                href.rsplit("/", 1)[-1]
                for href, slot in zip(spine_files, spine_slots)
                if slot in ("content", "back")
            }
            for href in result.toc_hrefs:
                basename = href.rsplit("/", 1)[-1]
                if basename not in allowed_toc_basenames:
                    result.errors.append(
                        f"printed toc.xhtml links to a non-content target: {basename!r}"
                    )
                    break

    if result.errors:
        result.ok = False
    return result

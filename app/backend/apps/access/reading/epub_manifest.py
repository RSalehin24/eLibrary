import re
import zipfile
from xml.etree import ElementTree

from .epub_archive import MAX_XML_BYTES, read_entry
from .epub_paths import InvalidEpub, referenced_path
from .navigation import publication_navigation

PACKAGE_NAMESPACE = {"opf": "http://www.idpf.org/2007/opf"}
CONTAINER_NAMESPACE = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
DOCUMENT_TYPES = {"application/xhtml+xml", "text/html"}
READER_MANIFEST_VERSION = 2


def read_xml(archive, entry):
    if entry.file_size > MAX_XML_BYTES:
        raise InvalidEpub("EPUB metadata exceeds the size limit.")
    text = read_entry(archive, entry).decode("utf-8-sig")
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
        raise InvalidEpub("EPUB XML declarations are unsupported.")
    return ElementTree.fromstring(text)


def publication_manifest(archive: zipfile.ZipFile, entries):
    container = read_xml(archive, entries["META-INF/container.xml"])
    rootfile = container.find("c:rootfiles/c:rootfile", CONTAINER_NAMESPACE)
    if rootfile is None:
        raise InvalidEpub("EPUB package is missing.")
    package_path = referenced_path("", rootfile.attrib["full-path"])
    package = read_xml(archive, entries[package_path])
    resources = manifest_resources(package, package_path, entries)
    chapters = spine_chapters(package, resources)
    return {
        "chapters": chapters,
        "resources": list(resources.values()),
        "navigation": publication_navigation(archive, resources, chapters),
    }


def manifest_resources(package, package_path, entries):
    resources = {}
    for item in package.findall("opf:manifest/opf:item", PACKAGE_NAMESPACE):
        identifier = item.attrib["id"]
        path = referenced_path(package_path, item.attrib["href"])
        if identifier in resources or path not in entries or entries[path].is_dir():
            raise InvalidEpub("Invalid EPUB manifest resource.")
        media_type = item.attrib["media-type"]
        if len(media_type) > 100 or not re.fullmatch(
            r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+", media_type
        ):
            raise InvalidEpub("Invalid EPUB resource media type.")
        resources[identifier] = {
            "path": path,
            "media_type": media_type,
            "size": entries[path].file_size,
            "href": item.attrib["href"],
            "navigation_type": "nav"
            if "nav" in item.attrib.get("properties", "").split()
            else "ncx"
            if media_type == "application/x-dtbncx+xml"
            else "",
        }
    return resources


def spine_chapters(package, resources):
    chapters: list[dict[str, str | int]] = []
    spine = package.find("opf:spine", PACKAGE_NAMESPACE)
    if spine is None:
        raise InvalidEpub("EPUB contains no readable chapters.")
    for index, item in enumerate(spine):
        resource = resources.get(item.attrib["idref"])
        if resource is None or resource["media_type"] not in DOCUMENT_TYPES:
            raise InvalidEpub("EPUB chapter is missing or unsupported.")
        if item.attrib.get("linear", "yes") != "no":
            chapters.append(
                {
                    "path": resource["path"],
                    "label": f"অধ্যায় {len(chapters) + 1}",
                    "spine_index": index,
                    "idref": item.attrib["idref"],
                    "spine_step": (list(package).index(spine) + 1) * 2,
                    "href": resource["href"],
                }
            )
    if not chapters:
        raise InvalidEpub("EPUB contains no readable chapters.")
    return chapters

import base64
import re
from urllib.parse import unquote, urlsplit

from apps.access.reading.epub_paths import InvalidEpub, referenced_path
from bs4 import BeautifulSoup

MAX_HTML_BYTES = 64 * 1024 * 1024
CSS_URL = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", re.IGNORECASE)


def require_passive_markup(data):
    document = BeautifulSoup(data, "html.parser")
    for element in document.find_all(True):
        if element.name in {"script", "iframe", "object", "embed"} or any(
            name.lower().startswith("on") for name in element.attrs
        ):
            raise InvalidEpub("Scripted EPUB resources cannot be imported.")
        for name in ("href", "src", "xlink:href"):
            if (
                urlsplit(str(element.get(name, "")).strip()).scheme.lower()
                == "javascript"
            ):
                raise InvalidEpub("Scripted EPUB resources cannot be imported.")


class HtmlResources:
    def __init__(self, publication, directory):
        self.directory = directory
        self.resources = {
            item["path"]: item for item in publication.manifest["resources"]
        }
        self.sections = {
            item["path"]: f"chapter-{index + 1}"
            for index, item in enumerate(publication.manifest["chapters"])
        }
        self.embedded_bytes = 0

    def bytes(self, path):
        if path not in self.resources:
            raise InvalidEpub("An EPUB resource is not declared in its package.")
        data = (self.directory / path).read_bytes()
        if len(data) != self.resources[path]["size"]:
            raise InvalidEpub("A prepared EPUB resource changed before conversion.")
        if self.resources[path]["media_type"] in {
            "image/svg+xml",
            "application/xhtml+xml",
            "text/html",
        }:
            require_passive_markup(data)
        return data

    def text(self, path):
        data = self.bytes(path)
        encoding = (
            "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        )
        try:
            return data.decode(encoding)
        except UnicodeError as error:
            raise InvalidEpub(
                "An EPUB text resource has an unsupported encoding."
            ) from error

    def anchor(self, base, reference):
        parsed = urlsplit(reference)
        target = referenced_path(base, reference) if parsed.path else base
        if target not in self.sections:
            raise InvalidEpub(
                "An EPUB link targets content outside the retained spine."
            )
        section = self.sections[target]
        fragment = unquote(parsed.fragment, errors="strict")
        return f"#{section}--{fragment}" if fragment else f"#{section}"

    def data_uri(self, base, reference):
        path = referenced_path(base, reference)
        media_type = self.resources.get(path, {}).get("media_type", "")
        if not media_type.startswith(
            ("image/", "audio/", "video/", "font/")
        ) and media_type not in {
            "application/font-woff",
            "application/font-sfnt",
            "application/vnd.ms-opentype",
        }:
            raise InvalidEpub("An EPUB content resource cannot be embedded safely.")
        encoded = base64.b64encode(self.bytes(path)).decode("ascii")
        self.embedded_bytes += len(encoded)
        if self.embedded_bytes > MAX_HTML_BYTES:
            raise InvalidEpub("The converted EPUB exceeds the HTML size limit.")
        fragment = urlsplit(reference).fragment
        return f"data:{media_type};base64,{encoded}" + (
            f"#{fragment}" if fragment else ""
        )

    def style(self, base, value):
        if re.search(
            r"@import|expression\s*\(|javascript\s*:|\\|<", value, re.IGNORECASE
        ):
            raise InvalidEpub("The EPUB stylesheet needs unsupported conversion.")
        return CSS_URL.sub(
            lambda match: (
                match[0]
                if match[2].strip().startswith("#")
                else f'url("{self.data_uri(base, match[2].strip())}")'
            ),
            value,
        )

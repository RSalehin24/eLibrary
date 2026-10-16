from html.parser import HTMLParser

from .epub_paths import InvalidEpub

PREPARATION_VERSION = 1


class NavigationTagFilter(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_offsets = [0]
        self.removals = []
        self.metadata_tags = []
        for index, character in enumerate(source):
            if character == "\n":
                self.line_offsets.append(index + 1)

    def handle_starttag(self, tag, attributes):
        tag_text = self.get_starttag_text()
        if tag_text is None:
            raise InvalidEpub("EPUB navigation markup is invalid.")
        attributes = dict(attributes)
        refresh = (
            tag == "meta"
            and (attributes.get("http-equiv") or "").strip().lower() == "refresh"
        )
        if tag == "meta" and not tag_text.rstrip().endswith("/>"):
            self.metadata_tags.append(refresh)
        if tag == "base" or refresh:
            line, column = self.getpos()
            start = self.line_offsets[line - 1] + column
            self.removals.append((start, start + len(tag_text)))

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)

    def handle_endtag(self, tag):
        removed_metadata = (
            tag == "meta" and self.metadata_tags and self.metadata_tags.pop()
        )
        if tag == "base" or removed_metadata:
            line, column = self.getpos()
            start = self.line_offsets[line - 1] + column
            self.removals.append((start, self.source.index(">", start) + 1))

    def filtered_source(self):
        self.feed(self.source)
        self.close()
        parts, start = [], 0
        for begin, end in self.removals:
            parts.append(self.source[start:begin])
            start = end
        parts.append(self.source[start:])
        return "".join(parts)


def safe_document(data):
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8"
    try:
        return (
            NavigationTagFilter(data.decode(encoding))
            .filtered_source()
            .encode(encoding)
        )
    except (UnicodeError, AssertionError) as exc:
        raise InvalidEpub("EPUB document encoding or markup is invalid.") from exc

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from . import book_manifest as manifest


class OutputFolderProvider(Protocol):
    def create_output_folder(self, title: str) -> str: ...


@dataclass(frozen=True)
class CollectionOptions:
    limits: dict[str, Any]
    page_cache: Any = None
    output_directory: Path | None = None
    cover_downloader: Callable[[str, str, Any], str] | None = None


class ManifestCollector:
    def __init__(self, context, options: CollectionOptions):
        self.context = context
        self.options = options

    def metadata(self, soup, url):
        title, title_author = manifest.extract_title_and_author(soup)
        terms = manifest.extract_entry_terms(soup)
        folder = self.options.output_directory
        if folder is None:
            folder = Path(
                cast(OutputFolderProvider, manifest.scraper).create_output_folder(title)
            )
        folder.mkdir(parents=True, exist_ok=True)
        cover_url = manifest.extract_cover_url(soup, url)
        download_cover = self.options.cover_downloader or manifest.download_cover_asset
        return {
            "title": title,
            "title_author": title_author,
            "terms": terms,
            "author": manifest.term_display(terms, "authors", "author") or title_author,
            "series": manifest.term_display(terms, "series"),
            "book_type": manifest.term_display(terms, "ld_course_category", "category"),
            "output_folder": str(folder),
            "cover_source_url": cover_url,
            "cover": download_cover(cover_url, str(folder), self.context.session),
        }

    def contents(self, soup, request):
        url, metadata = request
        landing = manifest.extract_entry_content_html(soup, metadata["title"])
        nodes, toc_metadata = manifest.collect_learndash_toc(
            soup, url, self.context, self.options.limits
        )
        soup.decompose()
        items = (
            manifest.collect_content_items(
                nodes,
                self.context,
                self.options.limits,
                page_cache=self.options.page_cache,
            )
            if nodes
            else []
        )
        sections = manifest.normalize_body_sections(
            book_title=metadata["title"],
            landing_main_content=landing,
            toc_nodes=nodes,
            content_items=items,
            author=metadata["author"],
            series=metadata["series"],
            book_type=metadata["book_type"],
        )
        structure = manifest.classify_manifest_structure(
            nodes,
            sections["content_items"],
            sections["main_content"],
            toc_metadata,
            limits=self.options.limits,
        )
        return nodes, sections, structure

    def document(self, url, parts):
        metadata, contents = parts
        nodes, sections, structure = contents
        projection = manifest.projection_from_manifest_parts(
            canonical_url=url,
            title=metadata["title"],
            author=metadata["author"],
            series=metadata["series"],
            book_type=metadata["book_type"],
            cover=metadata["cover"],
            cover_source_url=metadata["cover_source_url"],
            output_folder=metadata["output_folder"],
            sections_payload=sections,
        )
        if self.options.cover_downloader is not None:
            # Export assets are local files; the original URL remains provenance only.
            projection["cover"] = metadata["cover"]
        document = manifest.build_manifest_from_projection(
            url,
            projection,
            pages=self.context.pages,
            source_structure=structure,
            metadata={
                "entry_terms": metadata["terms"],
                "title_author": metadata["title_author"],
            },
        )
        document["toc_source"] = nodes
        return {
            "schema_version": manifest.CURRENT_MANIFEST_SCHEMA_VERSION,
            "source_url": url,
            "canonical_url": url,
            "pages": self.context.pages,
            "manifest": document,
            "raw_scrape_payload": projection,
        }

    def collect(self, url):
        soup = self.context.fetch_soup(url, kind="landing")
        if soup is None:
            return {
                "schema_version": manifest.CURRENT_MANIFEST_SCHEMA_VERSION,
                "source_url": url,
                "canonical_url": url,
                "pages": self.context.pages,
                "manifest": {},
                "raw_scrape_payload": {},
            }
        metadata = self.metadata(soup, url)
        contents = self.contents(soup, (url, metadata))
        return self.document(url, (metadata, contents))

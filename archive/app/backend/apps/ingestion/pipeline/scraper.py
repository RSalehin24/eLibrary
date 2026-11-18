"""Compatibility facade for the named scraper modules."""
from pathlib import Path as _Path

_MODULE_DIR = _Path(__file__).with_name("scraper_modules")
_MODULE_FILES = (
    "scrape_limits_and_header_cleanup.py",
    "front_matter_extraction.py",
    "metadata_and_inline_toc.py",
    "recursive_content_nodes.py",
    "lesson_collection.py",
    "book_scrape_entrypoint.py",

)

for _module_file in _MODULE_FILES:
    _module_path = _MODULE_DIR / _module_file
    exec(compile(_module_path.read_text(encoding="utf-8"), str(_module_path), "exec"), globals())

del _Path, _MODULE_DIR, _MODULE_FILES, _module_file, _module_path

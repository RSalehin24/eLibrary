import json
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag
from django.conf import settings

from apps.ingestion.services.normalization import extract_main_content_segments
from apps.common.text import clean_display_text
from .scraper_support.network import (
    _get_allowed_source_hosts,
    HEADERS,
    clean_buttons,
    create_session_with_retries,
    get_soup,
    normalize_source_url,
)
from .scraper_support.text import (
    extract_core_title,
    normalize_bengali_numbers,
    normalize_text,
    texts_are_similar,
)

INLINE_TOC_PATTERNS = ("সূচীপত্র", "সুচিপত্র", "সূচী", "table of contents", "contents")

DEFAULT_SCRAPE_LIMITS = {
    "max_nodes": 320,
    "max_depth": 6,
    "max_lesson_pages": 20,
    "max_content_chars": 120000,
}


def normalize_scrape_limits(content_limits=None):
    limits = dict(DEFAULT_SCRAPE_LIMITS)
    if not isinstance(content_limits, dict):
        return limits

    for key, default in DEFAULT_SCRAPE_LIMITS.items():
        raw_value = content_limits.get(key, default)
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            parsed = default
        limits[key] = max(1, parsed)

    return limits


def truncate_scraped_content(content, max_content_chars):
    if not content:
        return content

    if not isinstance(max_content_chars, int) or max_content_chars <= 0:
        return content

    if len(content) <= max_content_chars:
        return content

    return content[:max_content_chars]

def remove_redundant_headers(html_content, title, debug=False):
    """
    Remove redundant headers that match the title (with fuzzy matching that ignores symbols).
    Checks h1-h6 tags and <p><strong> combinations.
    Also removes duplicate section headers like "প্রথম খণ্ড" when title contains "১ম খণ্ড".
    Handles cases where content has title with extra info like author name.
    """
    if not html_content:
        return html_content
    
    soup = BeautifulSoup(html_content, "html.parser")
    removed_count = 0
    
    # Mapping of Bengali numerals to their word equivalents for section matching
    section_mappings = {
        'প্রথম': ['১ম', 'প্রথম', '1ম'],
        'দ্বিতীয়': ['২য়', 'দ্বিতীয়', '2য়'],
        'তৃতীয়': ['৩য়', 'তৃতীয়', '3য়'],
        'চতুর্থ': ['৪র্থ', 'চতুর্থ', '4র্থ'],
        'পঞ্চম': ['৫ম', 'পঞ্চম', '5ম'],
        'ষষ্ঠ': ['৬ষ্ঠ', 'ষষ্ঠ', '6ষ্ঠ'],
        'সপ্তম': ['৭ম', 'সপ্তম', '7ম'],
        'অষ্টম': ['৮ম', 'অষ্টম', '8ম'],
        'নবম': ['৯ম', 'নবম', '9ম'],
        'দশম': ['১০ম', 'দশম', '10ম'],
    }
    
    def is_section_duplicate(header_text, lesson_title):
        """
        Check if header_text is a duplicate of a section mentioned in lesson_title.
        E.g., "প্রথম খণ্ড" duplicates "১ম খণ্ড" in title
        """
        if not lesson_title:
            return False
            
        header_normalized = normalize_text(header_text)
        title_normalized = normalize_text(lesson_title)
        
        # Check for "খণ্ড" (section/part) duplicates
        if 'খণড' in header_normalized:  # normalized form of খণ্ড
            # Extract the section number/word from header
            for word, variants in section_mappings.items():
                word_normalized = normalize_text(word)
                if word_normalized in header_normalized:
                    # Check if any variant appears in the title
                    for variant in variants:
                        variant_normalized = normalize_text(variant)
                        if variant_normalized in title_normalized and 'খণড' in title_normalized:
                            return True
        
        return False
    
    def is_title_duplicate(header_text, main_title):
        """
        Check if header_text is a duplicate/variant of the main title.
        Handles cases like:
        - Exact match after normalization
        - One contains the other
        - Same core title with different author info
        - Number format variations (প্রথম vs ১ম)
        """
        if not main_title or not header_text:
            return False
        
        # Use the improved texts_are_similar function
        if texts_are_similar(header_text, main_title, debug=debug):
            return True
        
        # Extract core titles and compare
        header_core = extract_core_title(header_text)
        title_core = extract_core_title(main_title)
        
        if header_core and title_core:
            # Check if cores are similar
            if texts_are_similar(header_core, title_core, debug=False):
                return True
            
            # Check if one core contains the other
            if len(header_core) > 5 and len(title_core) > 5:
                if header_core in title_core or title_core in header_core:
                    return True
        
        return False
    
    # Remove headings that match the title (ignoring symbols)
    if title:
        # First, check all heading tags (h1-h6) - especially early ones
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for heading in headings:
            # Skip headings inside lists
            if heading.find_parent(['ol', 'ul']):
                continue
            
            text = heading.get_text(strip=True)
            if not text:
                continue
            
            # Use the improved title duplicate detection
            if is_title_duplicate(text, title):
                if debug:
                    print(f"  ✓ Removed title duplicate ({heading.name}): '{text}'")
                heading.decompose()
                removed_count += 1
            # Also check for section duplicates
            elif is_section_duplicate(text, title):
                if debug:
                    print(f"  ✓ Removed section duplicate ({heading.name}): '{text}'")
                heading.decompose()
                removed_count += 1
        
        # Second, check <p><strong> combinations
        paragraphs = soup.find_all('p')
        
        for p in paragraphs:
            # Skip paragraphs inside lists
            if p.find_parent(['ol', 'ul']):
                continue
            
            # Check if paragraph has a strong tag as direct child or main content
            strong_tags = p.find_all('strong', recursive=False)
            if not strong_tags:
                # Check all strong tags within the paragraph
                strong_tags = p.find_all('strong')
            
            for strong in strong_tags:
                strong_text = strong.get_text(strip=True)
                if not strong_text:
                    continue
                
                # Get paragraph text to see if it's mostly just the strong tag
                p_text = p.get_text(strip=True)
                
                # Check if strong text matches title
                if is_title_duplicate(strong_text, title):
                    # Also verify paragraph is mostly the strong text (not a longer paragraph mentioning the title)
                    p_text_norm = normalize_text(p_text)
                    strong_text_norm = normalize_text(strong_text)
                    # If paragraph is similar in length to strong text, it's likely a standalone title
                    if len(p_text_norm) < len(strong_text_norm) * 1.5:
                        if debug:
                            print(f"  ✓ Removed title duplicate (p>strong): '{p_text}'")
                        p.decompose()
                        removed_count += 1
                        break
                
                # Check if it's a section duplicate (e.g., "প্রথম খণ্ড" when title has "১ম খণ্ড")
                elif is_section_duplicate(strong_text, title):
                    if debug:
                        print(f"  ✓ Removed section duplicate (p>strong): '{p_text}' (matches section in title '{title}')")
                    p.decompose()
                    removed_count += 1
                    break
    
    if debug and removed_count > 0:
        print(f"  Total removed: {removed_count} redundant headers")
    
    return str(soup)


FRONT_MATTER_LABEL_PATTERNS = [
    "লেখক",
    "অনুবাদ",
    "অনুবাদক",
    "সম্পাদক",
    "সম্পাদ",
    "প্রকাশক",
    "প্রথম প্রকাশ",
    "প্রকাশকাল",
    "মূল",
    "edition",
    "publisher",
    "published",
    "translator",
    "author",
]

DEDICATION_PATTERNS = [
    "উৎসর্গ",
    "অনুবাদকের উৎসর্গ",
    "লেখকের উৎসর্গ",
    "dedication",
]

DEDICATION_INLINE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:অনুবাদকের\s+উৎসর্গ|লেখকের\s+উৎসর্গ|উৎসর্গ|dedication)\s*[:ঃ\-–—]?\s*",
    re.IGNORECASE,
)

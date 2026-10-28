"""Extract source obligations so heading coverage cannot hide missing details."""

from __future__ import annotations

import re
from collections.abc import Iterator

SourceReference = tuple[int, str]
TABLE_SECTIONS = {
    "decision": ("| Decision |", "### Clean development rebuild"),
    "issue": ("| ID | Issue or concern |", "### Audit every portion"),
    "page": ("| Page family |", "### A3."),
    "reader_feature": ("| Area |", "### B3. One command registry"),
    "command": ("| Action |", "### B4. Reader acceptance"),
    "stage": ("| Stage |", "### C4. Intelligence"),
    "service": ("| Service |", "### Integration requirements"),
    "milestone": ("| Milestone |", "### Verification matrix"),
    "route_area": ("| Area | Page route templates |", "### Related evidence"),
}


def table_references(
    source: str, bounds: tuple[str, str]
) -> dict[str, SourceReference]:
    start = source.index(bounds[0])
    block = source[start : source.index(bounds[1], start)]
    first_line = source[:start].count("\n") + 1
    references = {}
    for offset, line in enumerate(block.splitlines()):
        if offset >= 2 and line.startswith("|"):
            key = line.split("|")[1].strip().strip("*")
            if key in references:
                raise ValueError(f"Duplicate source table key: {key}")
            references[key] = (first_line + offset, line)
    return references


def content_lines(source: str) -> Iterator[tuple[int, str, str]]:
    heading, fenced = "Document context", False
    for number, line in enumerate(source.splitlines(), start=1):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not line.strip():
            continue
        if line.startswith("#"):
            heading = line.lstrip("# ")
        yield number, heading, line


def line_kind(line: str, heading: str) -> str | None:
    if heading == "Contents" or line.startswith("|"):
        return None
    if line.startswith(("## ", "### ")):
        return "section"
    if line.startswith("#"):
        return None
    if line.startswith("- "):
        return "bullet"
    return "numbered" if re.match(r"^\d+\. ", line) else "prose"


def reference_key(kind: str, heading: str, line: str) -> str:
    if kind == "section":
        return heading
    value = line[2:] if kind == "bullet" else line
    return f"{heading}: {value}"


def line_references(source: str) -> dict[str, dict[str, SourceReference]]:
    references: dict[str, dict[str, SourceReference]] = {}
    for number, heading, line in content_lines(source):
        kind = line_kind(line, heading)
        if kind is None:
            continue
        key = reference_key(kind, heading, line)
        group = references.setdefault(kind, {})
        if key in group:
            raise ValueError(f"Duplicate source clause: {key}")
        group[key] = (number, line)
    return references


def source_references(source: str) -> dict[str, dict[str, SourceReference]]:
    return {
        **{
            kind: table_references(source, bounds)
            for kind, bounds in TABLE_SECTIONS.items()
        },
        **line_references(source),
    }


def bullet_requirements(source: str) -> set[str]:
    return set(line_references(source).get("bullet", {}))


def source_requirements(source: str) -> dict[str, set[str]]:
    return {kind: set(group) for kind, group in source_references(source).items()}

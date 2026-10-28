"""Check planning coverage and references without starting application services."""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from plan_integrity import check_plan_fingerprints
from source_coverage import SourceReference, source_references, source_requirements

SOURCE_SHA256 = "46fd596d22b5f730f3b06fa8c2458c594d2f4a4cfb3efefa765cb2674ea78c96"
TASK_PATTERN = r"(?:F|W|R|E|REL)\d{2}"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def task_dependencies(plan_root: Path) -> dict[str, set[str]]:
    source = (plan_root / "shared/baseline-and-sequence.md").read_text()
    pattern = rf"^\| ({TASK_PATTERN}) \| M\d \| ([^|]+) \|"
    rows = re.findall(pattern, source, re.MULTILINE)
    require(len(rows) == len({row[0] for row in rows}), "Duplicate task IDs")
    return {
        task: set() if parents.strip() == "None" else set(parents.strip().split(";"))
        for task, parents in rows
    }


def check_task_graph(dependencies: dict[str, set[str]]) -> None:
    known = set(dependencies)
    referenced = set().union(*dependencies.values())
    require(referenced <= known, f"Unknown prerequisites: {referenced - known}")
    complete: set[str] = set()
    while complete != known:
        ready = {task for task in known - complete if dependencies[task] <= complete}
        require(bool(ready), f"Cyclic task dependencies: {known - complete}")
        complete.update(ready)
    require(dependencies["R01"] == {"W08"}, "Reader must follow website acceptance")
    require(dependencies["E01"] == {"R05"}, "Engine must follow reader acceptance")


def read_matrix(plan_root: Path) -> list[dict[str, str]]:
    path = plan_root / "shared/verification/requirements-matrix.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        require(
            reader.fieldnames
            == [
                "kind",
                "requirement",
                "source_key",
                "source_line",
                "source_text",
                "tasks",
                "plan",
                "plan_section",
                "verification",
            ],
            "Unexpected matrix columns",
        )
        return list(reader)


def check_matrix_rows(
    rows: list[dict[str, str]], plan_root: Path, tasks: set[str]
) -> None:
    identifiers = [row["requirement"] for row in rows]
    require(len(identifiers) == len(set(identifiers)), "Duplicate requirement IDs")
    assigned = {task for row in rows for task in row["tasks"].split(";")}
    require(assigned == tasks, f"Task coverage mismatch: {assigned ^ tasks}")
    for row in rows:
        require(
            all(isinstance(value, str) and value.strip() for value in row.values()),
            f"Empty or malformed row: {row}",
        )
        require(
            set(row["tasks"].split(";")) <= tasks, f"Unknown task: {row['requirement']}"
        )
        target = (plan_root / row["plan"]).resolve()
        require(
            target.is_relative_to(plan_root) and target.is_file(),
            f"Missing plan: {row['plan']}",
        )
        check_link(plan_root / "README.md", f"{row['plan']}#{row['plan_section']}")


def check_source_text(
    rows: list[dict[str, str]], references: dict[str, dict[str, SourceReference]]
) -> None:
    for row in rows:
        expected = references[row["kind"]][row["source_key"]]
        actual = (int(row["source_line"]), row["source_text"])
        require(actual == expected, f"Source clause mismatch: {row['requirement']}")


def check_coverage(rows: list[dict[str, str]], expected: dict[str, set[str]]) -> None:
    require(
        {row["kind"] for row in rows} == set(expected),
        "Unexpected requirement category",
    )
    for kind, keys in expected.items():
        actual = [row["source_key"] for row in rows if row["kind"] == kind]
        require(len(actual) == len(set(actual)), f"Duplicate {kind} source key")
        require(
            set(actual) == keys,
            f"{kind}: missing={keys - set(actual)}, extra={set(actual) - keys}",
        )


def heading_slug(heading: str) -> str:
    plain = re.sub(r"[`*_]", "", heading).lower()
    return re.sub(r"[^\w\- ]", "", plain).replace(" ", "-")


def local_link(path: Path, target: str) -> tuple[Path, str] | None:
    parsed = urlsplit(target.strip("<>"))
    if parsed.scheme or parsed.netloc:
        return None
    destination = path.parent / unquote(parsed.path) if parsed.path else path
    return destination.resolve(), unquote(parsed.fragment)


def check_link(path: Path, target: str) -> None:
    local = local_link(path, target)
    if local is None:
        return
    destination, fragment = local
    require(destination.exists(), f"Broken link in {path.name}: {target}")
    if fragment and destination.suffix == ".md":
        headings = re.findall(r"^#{1,6} (.+)$", destination.read_text(), re.MULTILINE)
        require(
            fragment in {heading_slug(value) for value in headings},
            f"Missing anchor: {target}",
        )


def check_markdown(paths: list[Path]) -> int:
    checked = 0
    for path in paths:
        targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text())
        for target in targets:
            check_link(path, target)
        checked += len(targets)
    return checked


def check_route_ownership(entries: list[tuple[str, str]]) -> None:
    removed = {route for route, owner in entries if owner.startswith("Remove")}
    require(
        removed == {"/physical-books/", "/[legacy]/"}, "Incorrect removal disposition"
    )
    reader = {route for route, owner in entries if owner.startswith("Reader")}
    require(
        reader == {"/reader/", "/reader/[identifier]/", "/local-reader/"},
        "Incorrect reader ownership",
    )


def check_routes(repo_root: Path, plan_root: Path) -> int:
    route_root = repo_root / "app/web/src/app"
    current = {
        "/" if path.parent == route_root else f"/{path.parent.relative_to(route_root)}/"
        for path in route_root.rglob("page.tsx")
    }
    matrix = (plan_root / "website/interface/design-and-route-matrix.md").read_text()
    entries = re.findall(r"^\| `(/[^`]*)` \| ([^|]+) \|", matrix, re.MULTILINE)
    declared = {route for route, _ in entries}
    require(len(entries) == len(declared), "Duplicate route matrix entries")
    check_route_ownership(entries)
    retired = {route for route, owner in entries if owner.strip() == "Remove W01"}
    require(
        declared - retired <= current <= declared,
        f"Route drift: missing={declared - retired - current}, extra={current - declared}",
    )
    return len(declared)


def check_repository_evidence(repo_root: Path) -> int:
    paths = (
        "AGENTS.md",
        "app/web/package.json",
        "app/web/README.md",
        "app/web/src/lib/reader-preferences.ts",
        "app/web/src/lib/progress-writer.ts",
        "app/backend/apps/catalog/models/books.py",
        "app/backend/apps/catalog/editorial/service.py",
        "app/backend/apps/common/permissions.py",
        "app/backend/apps/access/views/reader_v1.py",
        "app/backend/apps/access/reading/epub_archive.py",
        "app/backend/apps/ingestion/source_processing/export_verification.py",
        "app/backend/apps/ingestion/source_processing/policy.py",
        "app/backend/apps/ingestion/models/choices.py",
        "app/backend/apps/processing/automations/serializers.py",
        "tests/web/playwright.config.mjs",
        "tests/pytest.ini",
        "tests/scripts/verify.sh",
        "mypy.ini",
    )
    for path in paths:
        require((repo_root / path).is_file(), f"Repository evidence missing: {path}")
    return len(paths)


def check_placeholders(paths: list[Path]) -> None:
    pattern = r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b"
    for path in paths:
        require(
            not re.search(pattern, path.read_text()),
            f"Unresolved planning marker in {path}",
        )


def check_gap_audit(plan_root: Path) -> int:
    source = (plan_root / "shared/verification/gap-audit.md").read_text()
    rows = [
        line.split("|") for line in source.splitlines() if line.startswith("| GAP-")
    ]
    identifiers = [row[1].strip() for row in rows]
    require(bool(rows), "Gap audit has no findings")
    require(len(identifiers) == len(set(identifiers)), "Duplicate gap IDs")
    unresolved = [row[1].strip() for row in rows if row[-2].strip() != "Closed"]
    require(not unresolved, f"Unresolved planning findings: {unresolved}")
    return len(rows)


def reviewed_source(repo_root: Path) -> str:
    source_path = repo_root / "docs/application-reader-engine-plan.md"
    require(
        hashlib.sha256(source_path.read_bytes()).hexdigest() == SOURCE_SHA256,
        "Source specification changed; re-review the plans and update the reviewed fingerprint",
    )
    return source_path.read_text()


def report_scope(expected: dict[str, set[str]]) -> None:
    print(
        "Source coverage: "
        + "; ".join(f"{kind}={len(keys)}" for kind, keys in expected.items())
    )
    print(
        "Application behavior, model accuracy and visual acceptance are not established by this check."
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    plan_root = Path(__file__).resolve().parents[2]
    source = reviewed_source(repo_root)
    expected = source_requirements(source)
    dependencies = task_dependencies(plan_root)
    check_task_graph(dependencies)
    rows = read_matrix(plan_root)
    check_matrix_rows(rows, plan_root, set(dependencies))
    check_coverage(rows, expected)
    check_source_text(rows, source_references(source))
    paths = sorted(plan_root.rglob("*.md")) + [repo_root / "docs/README.md"]
    links = check_markdown(paths)
    check_placeholders(sorted(plan_root.rglob("*.md")))
    routes = check_routes(repo_root, plan_root)
    evidence = check_repository_evidence(repo_root)
    findings = check_gap_audit(plan_root)
    fingerprints = check_plan_fingerprints(plan_root)
    print(
        f"Planning verification passed: {len(rows)} exact source-to-section mappings; {len(dependencies)} acyclic tasks; {routes} routes; {links} links; {evidence} evidence paths; {findings} closed planning findings; {fingerprints} reviewed file fingerprints."
    )
    report_scope(expected)


if __name__ == "__main__":
    main()

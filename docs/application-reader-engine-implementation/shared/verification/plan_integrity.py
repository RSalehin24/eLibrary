"""Reject changed or unreviewed files after a whole-package document audit."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

MANIFEST = "shared/verification/reviewed-plan-files.csv"
REVIEWED_SUFFIXES = {".md", ".csv", ".py"}


def plan_files(plan_root: Path) -> dict[str, Path]:
    return {
        path.relative_to(plan_root).as_posix(): path
        for path in plan_root.rglob("*")
        if path.is_file()
        and path.suffix in REVIEWED_SUFFIXES
        and path.relative_to(plan_root).as_posix() != MANIFEST
    }


def recorded_fingerprints(plan_root: Path) -> dict[str, str]:
    with (plan_root / MANIFEST).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["path", "sha256"]:
            raise ValueError("Unexpected reviewed-file manifest columns")
        rows = list(reader)
    fingerprints = {row["path"]: row["sha256"] for row in rows}
    if len(fingerprints) != len(rows):
        raise ValueError("Duplicate reviewed plan files")
    return fingerprints


def check_plan_fingerprints(plan_root: Path) -> int:
    actual = plan_files(plan_root)
    reviewed = recorded_fingerprints(plan_root)
    if set(actual) != set(reviewed):
        raise ValueError(
            f"Reviewed file coverage mismatch: {set(actual) ^ set(reviewed)}"
        )
    changed = [
        name
        for name, path in actual.items()
        if hashlib.sha256(path.read_bytes()).hexdigest() != reviewed[name]
    ]
    if changed:
        raise ValueError(f"Changed plans require re-review: {changed}")
    return len(actual)

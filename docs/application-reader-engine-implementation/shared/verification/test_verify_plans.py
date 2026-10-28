"""Meaningful negative cases for the planning validator; no app services needed."""

from __future__ import annotations

import csv
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import verify_plans
from plan_integrity import MANIFEST, check_plan_fingerprints
from source_coverage import bullet_requirements, source_references, source_requirements

REPOSITORY = Path(__file__).resolve().parents[4]
PLANS = Path(__file__).resolve().parents[2]


class SourceCoverageTests(unittest.TestCase):
    def test_bullets_keep_section_identity(self):
        source = "## First\n- Same text\n## Second\n- Same text\n"
        self.assertEqual(
            bullet_requirements(source), {"First: Same text", "Second: Same text"}
        )

    def test_source_contains_leaf_obligations(self):
        expected = source_requirements(verify_plans.reviewed_source(REPOSITORY))
        sizes = {kind: len(expected[kind]) for kind in expected}
        self.assertEqual(sizes["reader_feature"], 12)
        self.assertEqual(sizes["command"], 17)
        self.assertEqual(sizes["stage"], 11)
        self.assertEqual(sizes["bullet"], 104)
        self.assertEqual(sizes["prose"], 44)
        self.assertEqual(sizes["numbered"], 9)
        self.assertEqual(sizes["service"], 3)
        self.assertEqual(sizes["milestone"], 6)
        self.assertEqual(sizes["route_area"], 21)


class PlanningValidationTests(unittest.TestCase):
    def setUp(self):
        self.dependencies = verify_plans.task_dependencies(PLANS)
        self.rows = verify_plans.read_matrix(PLANS)
        self.expected = source_requirements(verify_plans.reviewed_source(REPOSITORY))

    def test_current_requirements_and_dependencies_pass(self):
        verify_plans.check_task_graph(self.dependencies)
        verify_plans.check_matrix_rows(self.rows, PLANS, set(self.dependencies))
        verify_plans.check_coverage(self.rows, self.expected)

    def test_dependency_cycle_is_rejected(self):
        self.dependencies["F01"] = {"REL02"}
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            verify_plans.check_task_graph(self.dependencies)

    def test_unknown_prerequisite_is_rejected(self):
        self.dependencies["F01"] = {"UNKNOWN"}
        with self.assertRaisesRegex(ValueError, "Unknown prerequisites"):
            verify_plans.check_task_graph(self.dependencies)

    def test_skipped_website_gate_is_rejected(self):
        self.dependencies["R01"] = {"W07"}
        with self.assertRaisesRegex(ValueError, "website acceptance"):
            verify_plans.check_task_graph(self.dependencies)

    def test_missing_leaf_obligation_is_rejected(self):
        rows = [row for row in self.rows if row["source_key"] != "Opening"]
        with self.assertRaisesRegex(ValueError, "reader_feature"):
            verify_plans.check_coverage(rows, self.expected)

    def test_duplicate_requirement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate requirement"):
            verify_plans.check_matrix_rows(
                self.rows + [self.rows[0]], PLANS, set(self.dependencies)
            )

    def test_unknown_assigned_task_is_rejected(self):
        self.rows[0]["tasks"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "Task coverage"):
            verify_plans.check_matrix_rows(self.rows, PLANS, set(self.dependencies))

    def test_unmapped_task_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Task coverage"):
            verify_plans.check_matrix_rows(
                self.rows, PLANS, {*self.dependencies, "F03"}
            )

    def test_missing_plan_is_rejected(self):
        self.rows[0]["plan"] = "absent-document.md"
        with self.assertRaisesRegex(ValueError, "Missing plan"):
            verify_plans.check_matrix_rows(self.rows, PLANS, set(self.dependencies))

    def test_source_wording_is_checked_not_just_label(self):
        self.rows[0]["source_text"] = "Same label but missing its required behavior"
        references = source_references(verify_plans.reviewed_source(REPOSITORY))
        with self.assertRaisesRegex(ValueError, "Source clause mismatch"):
            verify_plans.check_source_text(self.rows, references)

    def test_wrong_source_line_is_rejected(self):
        self.rows[0]["source_line"] = "1"
        references = source_references(verify_plans.reviewed_source(REPOSITORY))
        with self.assertRaisesRegex(ValueError, "Source clause mismatch"):
            verify_plans.check_source_text(self.rows, references)

    def test_missing_plan_section_is_rejected(self):
        self.rows[0]["plan_section"] = "absent-plan-section"
        with self.assertRaisesRegex(ValueError, "Missing anchor"):
            verify_plans.check_matrix_rows(self.rows, PLANS, set(self.dependencies))


class LinkAndRouteTests(unittest.TestCase):
    def test_real_same_document_anchor_passes(self):
        verify_plans.check_link(PLANS / "README.md", "#folder-map")

    def test_broken_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Broken link"):
            verify_plans.check_link(PLANS / "README.md", "absent-document.md")

    def test_broken_same_document_anchor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing anchor"):
            verify_plans.check_link(PLANS / "README.md", "#absent-section")

    def test_current_route_inventory_passes(self):
        self.assertEqual(verify_plans.check_routes(REPOSITORY, PLANS), 54)

    def test_planned_removals_do_not_require_restoring_retired_pages(self):
        with TemporaryDirectory(prefix="elibrary-plan-routes-") as temporary:
            root = Path(temporary)
            self.copy_current_route_paths(root)
            self.assertEqual(verify_plans.check_routes(root, PLANS), 54)

    def test_missing_retained_page_is_rejected(self):
        with TemporaryDirectory(prefix="elibrary-plan-routes-") as temporary:
            root = Path(temporary)
            self.copy_current_route_paths(root, excluded="catalog/page.tsx")
            with self.assertRaisesRegex(ValueError, "Route drift.*catalog"):
                verify_plans.check_routes(root, PLANS)

    def test_unplanned_new_page_is_rejected(self):
        with TemporaryDirectory(prefix="elibrary-plan-routes-") as temporary:
            root = Path(temporary)
            self.copy_current_route_paths(root)
            extra = root / "app/web/src/app/unplanned/page.tsx"
            extra.parent.mkdir(parents=True)
            extra.touch()
            with self.assertRaisesRegex(ValueError, "Route drift.*unplanned"):
                verify_plans.check_routes(root, PLANS)

    def copy_current_route_paths(self, root: Path, excluded: str = ""):
        source = REPOSITORY / "app/web/src/app"
        for page in source.rglob("page.tsx"):
            relative = page.relative_to(source)
            if str(relative) == excluded:
                continue
            destination = root / "app/web/src/app" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.touch()

    def test_wrong_reader_ownership_is_rejected(self):
        entries = [
            ("/physical-books/", "Remove W01"),
            ("/[legacy]/", "Remove W01"),
        ]
        with self.assertRaisesRegex(ValueError, "Incorrect reader ownership"):
            verify_plans.check_route_ownership(entries)

    def test_missing_route_is_rejected(self):
        with TemporaryDirectory(prefix="elibrary-plan-review-") as temporary:
            self.assert_missing_catalog_route(Path(temporary))

    def assert_missing_catalog_route(self, temporary: Path):
        relative = Path("website/interface/design-and-route-matrix.md")
        lines = (PLANS / relative).read_text().splitlines(keepends=True)
        target = temporary / relative
        target.parent.mkdir(parents=True)
        target.write_text(
            "".join(line for line in lines if not line.startswith("| `/catalog/`"))
        )
        with self.assertRaisesRegex(ValueError, "Route drift"):
            verify_plans.check_routes(REPOSITORY, temporary)


class GapAuditTests(unittest.TestCase):
    def test_recorded_findings_are_closed(self):
        self.assertEqual(verify_plans.check_gap_audit(PLANS), 18)

    def test_reopened_finding_blocks_validation(self):
        with TemporaryDirectory(prefix="elibrary-plan-audit-") as temporary:
            root = Path(temporary)
            target = root / "shared/verification/gap-audit.md"
            target.parent.mkdir(parents=True)
            target.write_text("| GAP-01 | Example | Resolution | Open |\n")
            with self.assertRaisesRegex(ValueError, "Unresolved planning findings"):
                verify_plans.check_gap_audit(root)


class PlanFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="elibrary-plan-fingerprint-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.document = self.root / "README.md"
        self.document.write_text("# Reviewed plan\n")
        self.manifest = self.root / MANIFEST
        self.manifest.parent.mkdir(parents=True)
        with self.manifest.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["path", "sha256"])
            writer.writerow(
                ["README.md", hashlib.sha256(self.document.read_bytes()).hexdigest()]
            )

    def test_matching_reviewed_package_passes(self):
        self.assertEqual(check_plan_fingerprints(self.root), 1)

    def test_modified_plan_is_rejected(self):
        self.document.write_text("# Changed after review\n")
        with self.assertRaisesRegex(ValueError, "require re-review"):
            check_plan_fingerprints(self.root)

    def test_unreviewed_new_plan_is_rejected(self):
        (self.root / "additional-plan.md").write_text("# Not reviewed\n")
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            check_plan_fingerprints(self.root)

    def test_missing_reviewed_plan_is_rejected(self):
        self.document.rename(self.root / "renamed.md")
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            check_plan_fingerprints(self.root)

    def test_duplicate_manifest_entry_is_rejected(self):
        with self.manifest.open("a") as handle:
            handle.write("README.md,duplicate\n")
        with self.assertRaisesRegex(ValueError, "Duplicate reviewed"):
            check_plan_fingerprints(self.root)


if __name__ == "__main__":
    unittest.main()

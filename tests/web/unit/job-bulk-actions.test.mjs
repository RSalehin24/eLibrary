import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { availableBulkActions, bulkActionEntries } = await typescriptModule(new URL("../../../app/web/src/lib/job-bulk-actions.ts", import.meta.url));

test("failed source books offer explicit recovery rather than generic resume", () => {
  const job = { actions: [], source_recovery_actions: ["retry_source", "archive_book"] };
  assert.deepEqual(availableBulkActions(job), ["retry_source", "archive_book"]);
  assert.equal(availableBulkActions(job).includes("resume"), false);
  assert.deepEqual(availableBulkActions({ actions: ["pause", "cancel"] }), ["pause", "cancel"]);
});

test("bulk book commands pin both operation and book revisions", () => {
  const job = { id: "job-id", updated_at: "job-revision", book: { updated_at: "book-revision" } };
  assert.deepEqual(bulkActionEntries([job], "retry_source"), [{ id: "job-id", expected_updated_at: "job-revision" }]);
  for (const action of ["recreate_source", "archive_book"]) assert.deepEqual(bulkActionEntries([job], action), [{ id: "job-id", expected_updated_at: "job-revision", expected_book_updated_at: "book-revision" }]);
  assert.deepEqual(bulkActionEntries([{ id: "no-book", updated_at: "job-revision", book: null }], "recreate_source"), [{ id: "no-book", expected_updated_at: "job-revision" }]);
});

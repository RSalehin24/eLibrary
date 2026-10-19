import type { BackgroundJob, BulkJobControl } from "@/api/types";

export type JobBulkAction = BulkJobControl["action"];

export const sourceBulkActions = ["retry_source", "recreate_source", "archive_book"] as const;
export const sourceBulkActionLabels = {
  retry_source: "আবার চেষ্টা করুন",
  recreate_source: "ওয়েবসাইট থেকে নতুন করে তৈরি করুন",
  archive_book: "বই আর্কাইভে রাখুন",
};

export function availableBulkActions(job: BackgroundJob): string[] {
  return [...job.actions, ...(job.source_recovery_actions ?? [])];
}

export function bulkActionEntries(jobs: BackgroundJob[], action: JobBulkAction) {
  const bookAction = action === "recreate_source" || action === "archive_book";
  return jobs.map(job => ({ id: job.id, expected_updated_at: job.updated_at,
    ...(bookAction && job.book ? { expected_book_updated_at: job.book.updated_at } : {}),
  }));
}

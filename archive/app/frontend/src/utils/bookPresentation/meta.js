export const STATUS_META = {
  draft: { label: "Draft", description: "This record is still being prepared." },
  processing: { label: "Processing", description: "The system is still generating or organizing this book." },
  queued: { label: "Queued", description: "This task is waiting to start." },
  ready: { label: "Ready", description: "This book is ready to open and download." },
  published: { label: "Published", description: "This record has been finalized for readers." },
  archived: { label: "Archived", description: "This record is kept for reference." },
  pending: { label: "Awaiting review", description: "Metadata exists, but no one has reviewed it yet." },
  needs_review: { label: "Needs review", description: "This record should be checked before users rely on it." },
  approved: { label: "Reviewed", description: "Metadata has been reviewed and approved." },
  rejected: { label: "Needs correction", description: "A reviewer requested changes to this metadata." },
  pending_resolution: {
    label: "Requests",
    description: "This request still needs source matching before it can continue.",
  },
  ambiguous: { label: "Needs choice", description: "More than one possible source matched this title." },
  failed: { label: "Failed", description: "Something went wrong and needs attention." },
  cancelled: { label: "Stopped", description: "This task was stopped before it finished." },
  stopped: { label: "Stopped", description: "This task was stopped before it finished." },
  duplicate: { label: "Duplicate", description: "This request matches an existing book." },
  new: { label: "New", description: "This source has not been created locally yet." },
  unfinished: { label: "Unfinished", description: "This source still needs another processing pass." },
  deleted: { label: "Deleted", description: "This source points to a deleted local book." },
  succeeded: { label: "Ready", description: "The background job finished successfully." },
};

export function getStatusMeta(value) {
  if (!value) {
    return { label: "Unknown", description: "No status is available yet." };
  }
  return STATUS_META[value] || { label: value.replace(/_/g, " "), description: "" };
}

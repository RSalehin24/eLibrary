import type { SourceEntry } from "@/api/types";

export const sourceStatuses = { all: "সব উৎস", unlinked: "বইয়ের তালিকায় যুক্ত হয়নি", linked: "বইয়ের তালিকায় যুক্ত", updated: "আপডেট আছে", removed: "অপসারিত বইয়ের সঙ্গে যুক্ত" };

export function sourceStatus(entry: SourceEntry) {
  return entry.book?.deleted_at ? sourceStatuses.removed : entry.book ? sourceStatuses.linked : sourceStatuses.unlinked;
}

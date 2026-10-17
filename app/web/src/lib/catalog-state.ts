import type { ManagedBookDetail } from "../api/types";

const labels: Readonly<Record<string, string>> = {
  draft: "খসড়া", processing: "প্রক্রিয়াধীন", needs_review: "খসড়া",
  ready: "প্রস্তুত", published: "প্রকাশিত", archived: "আর্কাইভে", soft_deleted: "অপসারিত",
} satisfies Record<ManagedBookDetail["state"], string>;

export function catalogStateLabel(state: string) {
  return Object.hasOwn(labels, state) ? labels[state] : state;
}

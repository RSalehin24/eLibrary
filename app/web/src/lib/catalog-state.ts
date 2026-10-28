import type { ManagedBookDetail } from "../api/types";

const labels: Readonly<Record<string, string>> = {
  draft: "প্রকাশিত নয়", processing: "প্রক্রিয়াধীন", failed: "প্রস্তুতি ব্যর্থ",
  ready: "প্রস্তুত", published: "প্রকাশিত", archived: "আর্কাইভে", soft_deleted: "অপসারিত",
} satisfies Record<ManagedBookDetail["state"], string>;

export function catalogStateLabel(state: string) {
  return Object.hasOwn(labels, state) ? labels[state] : state;
}

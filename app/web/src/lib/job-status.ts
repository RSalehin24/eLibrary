import type { BackgroundJob, JobControl } from "../api/types";

export const jobStates: Record<BackgroundJob["state"], string> = {
  queued: "অপেক্ষমাণ", running: "কাজ চলছে", retry_wait: "আবার চেষ্টার অপেক্ষায়", paused: "স্থগিত", cancelled: "বাতিল",
  succeeded: "সম্পন্ন", failed: "ব্যর্থ", needs_attention: "পরীক্ষা করা প্রয়োজন",
};
export const jobActions: Record<JobControl["action"], string> = { pause: "স্থগিত করুন", cancel: "বাতিল করুন", resume: "আবার চালু করুন" };
export function jobActionLabel(kind: BackgroundJob["kind"], action: JobControl["action"]) {
  if (kind === "process_catalog" && action === "pause") return "কাজ যোগ করা স্থগিত করুন";
  if (kind === "process_catalog" && action === "cancel") return "কাজ যোগ করা বন্ধ করুন";
  return jobActions[action];
}
export const jobKinds: Record<BackgroundJob["kind"], string> = { prepare_epub: "পড়ার জন্য EPUB প্রস্তুত", deliver_kindle: "কিন্ডলে পাঠানো", account_mail: "অ্যাকাউন্টের ইমেইল", process_source: "উৎস থেকে বই প্রস্তুত", discover_source: "বইয়ের উৎস আবিষ্কার", process_catalog: "সব বই তৈরি করুন" };
const stages: Readonly<Record<string, string>> = {
  claimed: "কাজ নেওয়া হয়েছে", preparing: "EPUB পরীক্ষা ও প্রস্তুতি", prepared: "পড়ার উপকরণ প্রস্তুত", sending: "ইমেইল জমা দেওয়া হচ্ছে",
  fetching_source: "উৎসের লেখা সংগ্রহ", source_curated: "উৎসের লেখা যাচাই সম্পন্ন", source_duplicate: "একই নামে বইয়ের মিল পাওয়া গেছে",
  generating_exports: "HTML ও EPUB তৈরি হচ্ছে", source_exports_generated: "HTML ও EPUB তৈরি হয়েছে", publishing_source_assets: "উপকরণ সংরক্ষণ হচ্ছে", source_prepared: "বই পড়ার জন্য প্রস্তুত", publishing_source: "বই প্রকাশ করা হচ্ছে", source_published: "বই প্রকাশিত হয়েছে",
  saving_source_catalog: "উৎসের পরিচিতি সংরক্ষণ", source_catalog_page_saved: "উৎসের পাতা সংরক্ষিত", source_catalog_discovered: "উৎসের পরিচিতি সংগৃহীত",
  scheduling_source_processing: "নির্ধারিত বই প্রস্তুতির অনুরোধ সংরক্ষণ",
  queueing_catalog_books: "কাজ যোগ হচ্ছে", catalog_books_queued: "বইয়ের কাজ যোগ হয়েছে",
};
const activeStates = new Set(["queued", "running", "retry_wait"]);

export function jobStage(stage: string | null) {
  return stage ? stages[stage] ?? "প্রক্রিয়াকরণ" : "শুরু হয়নি";
}

export function jobPollingInterval(jobs: readonly Pick<BackgroundJob, "state">[], failureCount: number) {
  return activityPollingInterval(jobs.some((job) => activeStates.has(job.state)), failureCount);
}

export function activityPollingInterval(active: boolean, failureCount: number) {
  if (failureCount) return Math.min(60_000, 5_000 * 2 ** Math.min(failureCount, 4));
  return active ? 2_000 : 15_000;
}

export function isJobAction(action: string): action is JobControl["action"] {
  return action === "pause" || action === "cancel" || action === "resume";
}

export function jobTimestamp(value: string | null, language = "bn") {
  if (!value) return "—";
  const date = new Date(value);
  const numberingSystem = language === "bn" ? "beng" : "latn";
  const timeZone = "Asia/Dhaka";
  const day = new Intl.DateTimeFormat(language, { dateStyle: "long", timeZone, numberingSystem }).format(date);
  const time = new Intl.DateTimeFormat(language, { hour: "numeric", minute: "2-digit", hourCycle: "h12", ...(language === "bn" ? { dayPeriod: "short" as const } : {}), timeZone, numberingSystem }).format(date);
  return `${day}, ${time}${language === "bn" ? " (ঢাকা)" : " (Dhaka)"}`;
}

import { jobKinds, jobStates } from "./job-status";

export const jobViewLabels: Readonly<Record<string, string>> = { active: "চলমান কাজ", history: "আগের কাজ", recovery: "পুনরুদ্ধারের কাজ" };
export const jobCoverageLabels: Readonly<Record<string, string>> = { verified: "লেখার যাচাই সফল", incomplete: "লেখার যাচাই অসম্পূর্ণ", unverified: "লেখার যাচাই বাকি" };
export const jobLayoutLabels: Readonly<Record<string, string>> = { multi_page: "একাধিক পাতায় সূচিপত্র", complex: "একাধিক পাতা বা স্তরের সূচিপত্র", nested: "একাধিক স্তরের সূচিপত্র", inline: "এক পাতায় মূল লেখা", unclassified: "সূচিপত্রের তথ্য পাওয়া যায়নি" };
export const jobFilterKeys = ["q", "view", "state", "kind", "book", "parent_job", "automation_run", "error_code", "coverage", "layout"] as const;
const identifiers = new Set(["book", "parent_job", "automation_run"]);
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function savedQueueFilter(parameters: Record<string, unknown>): Record<string, string> | null {
  if (Object.entries(parameters).some(([key, value]) => !jobFilterKeys.includes(key as typeof jobFilterKeys[number]) || typeof value !== "string" || value.length > 255)) return null;
  const values = Object.fromEntries(Object.entries(parameters).filter(([, value]) => value).map(([key, value]) => [key, String(value)]));
  for (const [key, labels] of [["view", jobViewLabels], ["state", jobStates], ["kind", jobKinds], ["coverage", jobCoverageLabels], ["layout", jobLayoutLabels]] as const) {
    if (values[key] && !Object.hasOwn(labels, values[key])) return null;
  }
  if ((values.q?.length ?? 0) > 120 || values.error_code && !/^[a-z][a-z0-9_]{0,63}$/.test(values.error_code)) return null;
  if (Object.entries(values).some(([key, value]) => identifiers.has(key) && !uuidPattern.test(value))) return null;
  return values;
}

export function jobFilterQuery(values: Record<string, string>) {
  return new URLSearchParams(Object.entries(values).filter(([key, value]) => value && jobFilterKeys.includes(key as typeof jobFilterKeys[number]))).toString();
}

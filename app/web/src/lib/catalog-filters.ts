import { currentBrowseFilters } from "./browse-filters";
export const catalogFilterKeys = ["contributor", "contributor_role", "category", "series", "collection", "ownership", "sort"] as const;
export type CatalogFilters = Readonly<Record<string, string>>;
export const catalogSortLabels = {
  "": "সেরা মিল", "-created_at": "নতুন বই আগে", created_at: "পুরোনো বই আগে",
  title: "নাম অনুসারে", "-title": "নামের উল্টো ক্রমে", catalog_code: "কোড: ছোট থেকে বড়", "-catalog_code": "কোড: বড় থেকে ছোট",
  "-requested_at": "সংগ্রহে নতুন যোগ করা বই আগে", requested_at: "সংগ্রহে আগে যোগ করা বই আগে",
  publisher: "প্রকাশকের নাম অনুসারে", "-publisher": "প্রকাশকের নামের উল্টো ক্রমে",
};
export function catalogFilterQuery(values: CatalogFilters) {
  return new URLSearchParams(Object.entries(currentBrowseFilters(values)).filter(([, value]) => value !== "")).toString();
}

export function catalogNeedsAccount(values: CatalogFilters) {
  return values.ownership === "mine" || ["requested_at", "-requested_at"].includes(values.sort ?? "");
}

export function catalogHasConditions(values: CatalogFilters) {
  return Object.values(currentBrowseFilters(values)).some(value => value !== "");
}

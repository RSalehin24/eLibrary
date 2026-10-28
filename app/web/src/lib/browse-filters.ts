import type { RouteQuery } from "./route-query";

const retiredFilters = new Set(["record_type", "book_type", "review_state", "binding", "manual_price", "created_after", "created_before", "from_date", "to_date", "requested_after", "requested_before", "added_after", "added_before"]);

export function currentBrowseFilters<Value>(values: Readonly<Record<string, Value>>): Record<string, Value> {
  return Object.fromEntries(Object.entries(values).filter(([key]) => !retiredFilters.has(key)));
}

export function retiredFilterRedirect(pathname: string, parameters: RouteQuery) {
  if (!Object.keys(parameters).some(key => retiredFilters.has(key))) return null;
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(parameters)) {
    if (retiredFilters.has(key) || key === "page" || value === undefined) continue;
    for (const entry of Array.isArray(value) ? value : [value]) query.append(key, entry);
  }
  return `${pathname}${query.size ? `?${query}` : ""}`;
}

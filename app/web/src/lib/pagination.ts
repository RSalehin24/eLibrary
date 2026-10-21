export type PaginationItem = number | "gap-before" | "gap-after";

export function paginationItems(page: number, totalPages: number, slots = 7): PaginationItem[] {
  if (!Number.isSafeInteger(page) || !Number.isSafeInteger(totalPages) || page < 1 || totalPages < 1 || page > totalPages) return [];
  if (totalPages <= slots) return Array.from({ length: totalPages }, (_, index) => index + 1);
  const radius = Math.floor((slots - 4) / 2);
  const windowSize = slots - 2;
  if (page <= windowSize - radius) return [...Array.from({ length: windowSize }, (_, index) => index + 1), "gap-after", totalPages];
  if (page >= totalPages - windowSize + radius + 1) return [1, "gap-before", ...Array.from({ length: windowSize }, (_, index) => totalPages - windowSize + index + 1)];
  return [1, "gap-before", ...Array.from({ length: radius * 2 + 1 }, (_, index) => page - radius + index), "gap-after", totalPages];
}

export function paginationURL(page: number, destination: { pathname?: string; query?: string }) {
  const parameters = new URLSearchParams(destination.query);
  parameters.delete("cursor");
  parameters.set("page", String(page));
  return `${destination.pathname ?? ""}?${parameters}`;
}

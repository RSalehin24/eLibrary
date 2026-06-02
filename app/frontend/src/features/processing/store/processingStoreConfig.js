export const PROCESSING_ROUTE_PAGES = {
  "/catalog": "catalog",
  "/create": "create",
  "/on-hold": "on-hold",
  "/incomplete": "incomplete",
  "/multipage-toc": "multipage",
};

export const PROCESSING_SYNC_SCOPE_CATALOG = "catalog";
export const PROCESSING_SYNC_SCOPE_INCOMPLETE = "incomplete";

export const PROCESSING_CARD_KEYS = [
  "catalog-overview",
  "catalog-sync",
  "catalog-automation",
  "catalog-records",
  "create-overview",
  "create-requests",
  "create-queue",
  "create-processing",
  "create-created",
  "on-hold-overview",
  "on-hold-paused",
  "on-hold-failed",
  "on-hold-duplicate",
  "on-hold-deleted",
  "incomplete-overview",
  "incomplete-automation",
  "incomplete-records",
  "incomplete-completed",
  "multipage-records",
];

export const SHARED_PROCESSING_CARD_KEYS = new Set([
  "catalog-overview",
  "catalog-sync",
  "catalog-automation",
  "create-overview",
  "on-hold-overview",
  "incomplete-overview",
  "incomplete-automation",
]);

export function scopedSyncPath(scope, action) {
  return `/processing/sync/${scope}/${action}/`;
}

export function processingPath(path) {
  return path.includes("?")
    ? `${path}&includeLists=0`
    : `${path}?includeLists=0`;
}

export function processingPageForPathname(pathname) {
  return PROCESSING_ROUTE_PAGES[pathname] || "";
}

export function normalizeVersionValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function versionSignature(versions, domains) {
  return domains
    .map((domain) => `${domain}:${normalizeVersionValue(versions?.[domain])}`)
    .join("|");
}

export function catalogRemotePages(remotePages) {
  if (
    Array.isArray(remotePages) &&
    remotePages.every(
      (page) =>
        Array.isArray(page) &&
        page.every(
          (item) => item && typeof item === "object" && !Array.isArray(item),
        ),
    )
  ) {
    return remotePages;
  }
  return [];
}

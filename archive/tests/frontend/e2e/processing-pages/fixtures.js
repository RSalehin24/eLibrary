export const PROCESSING_TIMEOUT_MS = 20 * 60 * 1000;
export const SYNC_RUN_MODE_MANUAL = "manual";
export const SYNC_RUN_MODE_CATALOG_AUTOMATION = "catalog_automation";
export const SYNC_RUN_MODE_INCOMPLETE_AUTOMATION = "incomplete_automation";
export const CATALOG_SYNC_PHASE = "sync";
export const CATALOG_REQUEST_CREATION_PHASE = "request_creation";
export const CATALOG_PHASE_STATUS_NOT_STARTED = "not_started";
export const CATALOG_PHASE_STATUS_RUNNING = "running";
export const CATALOG_PHASE_STATUS_PAUSING = "pausing";
export const CATALOG_PHASE_STATUS_PAUSED = "paused";
export const CATALOG_PHASE_STATUS_COMPLETED = "completed";
export const PROCESSING_CARD_KEYS = ["catalog-overview", "catalog-sync", "catalog-automation", "catalog-records", "create-overview", "create-requests", "create-queue", "create-processing", "create-created", "on-hold-overview", "on-hold-paused", "on-hold-failed", "on-hold-duplicate", "on-hold-deleted", "incomplete-overview", "incomplete-automation", "incomplete-records", "incomplete-completed"];
export const INCOMPLETE_CATEGORY_KEYWORDS = ["incomplete", "unfinished", "অসম্পূর্ণ", "অসম্পূর্ণ বই"];
export const sessionPayload = {
  authenticated: true,
  user: {
    id: "processing-user",
    email: "processing-admin@example.com",
    full_name: "Processing Admin",
    is_superuser: true,
    capabilities: ["processing:manage"],
    totp_setup_required: false
  }
};
export function iso(offsetMinutes = 0) {
  return new Date(Date.UTC(2026, 3, 17, 8, offsetMinutes, 0)).toISOString();
}
export function record(overrides = {}) {
  return {
    id: "record-1",
    name: "Reusable Systems",
    url: "https://example.test/books/reusable-systems",
    category: "Architecture",
    writer: "Ada Writer",
    translator: null,
    composer: null,
    publisher: "North Press",
    createdAt: iso(1),
    updatedAt: iso(1),
    bookCreationState: "not_created",
    ...overrides
  };
}
export function request(overrides = {}) {
  return {
    id: "request-1",
    bookRecordId: "record-1",
    state: "initial",
    createdAt: iso(2),
    updatedAt: iso(2),
    progress: null,
    errorMessage: null,
    isResumed: false,
    isConfirmedNotDuplicate: false,
    duplicateOfRequestId: null,
    duplicateOfRecordId: null,
    linkedBookId: null,
    linkedBookSlug: null,
    ...overrides
  };
}
export function baseState(overrides = {}) {
  return {
    records: [],
    requests: [],
    sync: {
      status: "idle",
      phase: "sync",
      progress: null,
      fetchedCount: 0,
      skippedCount: 0,
      updatedCount: 0,
      appendedCount: 0,
      message: "Ready to sync.",
      remotePages: [],
      pageIndex: 0,
      runMode: SYNC_RUN_MODE_MANUAL
    },
    automation: {
      catalog: {
        enabled: false,
        interval: "weekly",
        time: "03:00",
        saved: false,
        lastRunAt: ""
      },
      incomplete: {
        enabled: false,
        interval: "weekly",
        time: "03:00",
        saved: false,
        lastRunAt: ""
      }
    },
    orchestration: {
      manualPipelineAdvance: true
    },
    ui: {
      actionDelayMs: 80,
      pipelineDelayMs: 500
    },
    ...overrides
  };
}
export async function mockAuthenticatedSession(page) {
  await page.route("**/api/auth/session/", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload)
    });
  });
  await page.route("**/api/csrf/", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "ok"
      })
    });
  });
  await page.route("**/api/catalog/books/**", async route => {
    const url = new URL(route.request().url());
    const pageNumber = Number(url.searchParams.get("page") || "1");
    const limit = Number(url.searchParams.get("limit") || "60");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        entries: [],
        pagination: {
          page: pageNumber,
          limit,
          total_count: 0,
          page_count: 1,
          has_previous: false,
          has_next: false
        }
      })
    });
  });
}

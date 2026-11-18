import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("create page cards isolate loaders and move requests between states", async ({
    page
  }) => {
    await boot(page, "/create", baseState({
      records: [record({
        id: "initial-a",
        name: "Initial A",
        category: "Poetry"
      }), record({
        id: "initial-b",
        name: "Initial B",
        category: "Poetry"
      }), record({
        id: "queued-a",
        name: "Queued A",
        category: "Science"
      }), record({
        id: "processing-a",
        name: "Processing A",
        category: "Science"
      }), record({
        id: "created-a",
        name: "Created A",
        category: "History"
      })],
      requests: [request({
        id: "initial-a-request",
        bookRecordId: "initial-a",
        state: "initial"
      }), request({
        id: "initial-b-request",
        bookRecordId: "initial-b",
        state: "initial"
      }), request({
        id: "queued-a-request",
        bookRecordId: "queued-a",
        state: "queued"
      }), request({
        id: "processing-a-request",
        bookRecordId: "processing-a",
        state: "processing"
      }), request({
        id: "created-a-request",
        bookRecordId: "created-a",
        state: "created",
        linkedBookId: "created-a-book-id",
        linkedBookSlug: "created-a-book"
      })],
      ui: {
        actionDelayMs: 400,
        pipelineDelayMs: 20_000
      }
    }));
    await expect(page.getByTestId("create-overview-stat-requests")).toContainText("2");
    await expectVisibleCount(page, "create", "requests", 2);
    await expectVisibleCount(page, "create", "queue", 1);
    await expectVisibleCount(page, "create", "processing", 1);
    await expectVisibleCount(page, "create", "created", 1);
    await expect(row(page, "create", "created", "created-a-request").getByRole("link", {
      name: "Open"
    })).toHaveAttribute("href", "/books/created-a-book");
    await page.getByTestId("create-requests-search").fill("initial a");
    await expectVisibleCount(page, "create", "requests", 1);
    await page.getByTestId("create-requests-search").fill("");
    await openCardFilters(page, "create", "requests");
    await page.getByTestId("create-requests-category-filter").selectOption("Poetry");
    await expect(page.getByTestId("create-requests-active-filters")).toContainText("Poetry");
    await expectVisibleCount(page, "create", "requests", 2);
    await checkbox(page, "create", "requests", "initial-a-request").check();
    await checkbox(page, "create", "requests", "initial-b-request").check();
    await page.getByTestId("create-requests-delete-btn").click();
    await expect(page.getByTestId("create-requests-loader")).toBeVisible();
    await expect(page.getByTestId("create-requests-delete-btn")).toBeDisabled();
    await expect(checkbox(page, "create", "queue", "queued-a-request")).toBeEnabled();
    await expect(page.getByTestId("create-requests-loader")).toHaveCount(0);
    await expectVisibleCount(page, "create", "requests", 0);
    await checkbox(page, "create", "processing", "processing-a-request").check();
    await page.getByTestId("create-processing-pause-btn").click();
    await expect(page.getByTestId("create-processing-loader")).toBeVisible();
    await expect(row(page, "create", "processing", "processing-a-request")).toHaveCount(0);
    await page.goto("/on-hold");
    await expect(row(page, "on-hold", "paused", "processing-a-request")).toBeVisible();
    await expect(row(page, "on-hold", "paused", "processing-a-request")).toContainText("Paused at processing");
    await page.goto("/create");
    await checkbox(page, "create", "created", "created-a-request").check();
    await page.getByTestId("create-created-delete-btn").click();
    await expect(row(page, "create", "created", "created-a-request")).toHaveCount(0);
    await page.goto("/on-hold");
    await expect(row(page, "on-hold", "deleted", "created-a-request")).toBeVisible();
  });
  test("on-hold page resumes, retries, resolves duplicates, deletes, and recreates", async ({
    page
  }) => {
    await boot(page, "/on-hold", baseState({
      records: [record({
        id: "paused-book",
        name: "Paused Book"
      }), record({
        id: "failed-book",
        name: "Failed Book"
      }), record({
        id: "duplicate-book",
        name: "Duplicate Book"
      }), record({
        id: "deleted-book",
        name: "Deleted Book"
      }), record({
        id: "original-book",
        name: "Original Book",
        bookCreationState: "processing"
      })],
      requests: [request({
        id: "paused-request",
        bookRecordId: "paused-book",
        state: "paused",
        progress: {
          savedAt: iso(20),
          checkpoint: "chapter-4",
          savedData: {
            chapters: 4
          }
        }
      }), request({
        id: "failed-request",
        bookRecordId: "failed-book",
        state: "failed",
        errorMessage: "Retry threshold exceeded"
      }), request({
        id: "duplicate-request",
        bookRecordId: "duplicate-book",
        state: "duplicate",
        duplicateOfRequestId: "original-request",
        duplicateOfRecordId: "original-book"
      }), request({
        id: "deleted-request",
        bookRecordId: "deleted-book",
        state: "deleted"
      }), request({
        id: "original-request",
        bookRecordId: "original-book",
        state: "processing"
      })],
      ui: {
        actionDelayMs: 120,
        pipelineDelayMs: 20_000
      }
    }));
    await expect(page.getByTestId("on-hold-overview-stat-paused")).toContainText("1");
    await expect(page.getByTestId("on-hold-failed-table")).toContainText("Error Reason");
    await expect(row(page, "on-hold", "paused", "paused-request")).toContainText("chapter-4");
    await expect(row(page, "on-hold", "failed", "failed-request")).toContainText("Retry threshold exceeded");
    await checkbox(page, "on-hold", "paused", "paused-request").check();
    await page.getByTestId("on-hold-paused-resume-btn").click();
    await expect(page.getByTestId("on-hold-paused-loader")).toBeVisible();
    await expect(row(page, "on-hold", "paused", "paused-request")).toHaveCount(0);
    await page.goto("/create");
    await expect(row(page, "create", "requests", "paused-request")).toBeVisible();
    await page.goto("/on-hold");
    await checkbox(page, "on-hold", "failed", "failed-request").check();
    await page.getByTestId("on-hold-failed-retry-btn").click();
    await expect(row(page, "on-hold", "failed", "failed-request")).toHaveCount(0);
    await page.goto("/create");
    await expect(row(page, "create", "requests", "failed-request")).toBeVisible();
    await page.goto("/on-hold");
    await checkbox(page, "on-hold", "duplicate", "duplicate-request").check();
    await page.getByTestId("on-hold-duplicate-new-btn").click();
    await expect(row(page, "on-hold", "duplicate", "duplicate-request")).toHaveCount(0);
    await page.goto("/create");
    await expect(row(page, "create", "requests", "duplicate-request")).toBeVisible();
    await page.goto("/on-hold");
    await checkbox(page, "on-hold", "deleted", "deleted-request").check();
    await page.getByTestId("on-hold-deleted-create-again-btn").click();
    await expect(row(page, "on-hold", "deleted", "deleted-request")).toHaveCount(0);
    await page.goto("/create");
    await expect(row(page, "create", "requests", "deleted-request")).toBeVisible();
  });
});

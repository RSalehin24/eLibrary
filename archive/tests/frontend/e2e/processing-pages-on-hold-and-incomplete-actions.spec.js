import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("on-hold cards show only their own status records", async ({
    page
  }) => {
    await boot(page, "/on-hold", baseState({
      records: [record({
        id: "paused-only-book",
        name: "Paused Only"
      }), record({
        id: "failed-only-book",
        name: "Failed Only"
      }), record({
        id: "duplicate-only-book",
        name: "Duplicate Only"
      }), record({
        id: "deleted-only-book",
        name: "Deleted Only"
      })],
      requests: [request({
        id: "paused-only-request",
        bookRecordId: "paused-only-book",
        state: "paused",
        progress: {
          savedAt: iso(21),
          checkpoint: "saved-chapter",
          savedData: {
            chapter: 7
          }
        }
      }), request({
        id: "failed-only-request",
        bookRecordId: "failed-only-book",
        state: "failed",
        errorMessage: "Pipeline failed after retries."
      }), request({
        id: "duplicate-only-request",
        bookRecordId: "duplicate-only-book",
        state: "duplicate",
        duplicateOfRequestId: "original-request",
        duplicateOfRecordId: "original-book"
      }), request({
        id: "deleted-only-request",
        bookRecordId: "deleted-only-book",
        state: "deleted"
      })],
      ui: {
        ...baseState().ui,
        pipelineDelayMs: 60_000
      }
    }));
    await expectVisibleCount(page, "on-hold", "paused", 1);
    await expectVisibleCount(page, "on-hold", "failed", 1);
    await expectVisibleCount(page, "on-hold", "duplicate", 1);
    await expectVisibleCount(page, "on-hold", "deleted", 1);
    await expect(row(page, "on-hold", "paused", "paused-only-request")).toBeVisible();
    await expect(row(page, "on-hold", "paused", "paused-only-request")).toContainText("Paused");
    await expect(row(page, "on-hold", "paused", "paused-only-request")).toContainText("saved-chapter");
    await expect(row(page, "on-hold", "paused", "failed-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "paused", "duplicate-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "paused", "deleted-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "failed", "failed-only-request")).toBeVisible();
    await expect(row(page, "on-hold", "failed", "failed-only-request")).toContainText("Failed");
    await expect(row(page, "on-hold", "failed", "failed-only-request")).toContainText("Pipeline failed after retries.");
    await expect(row(page, "on-hold", "failed", "paused-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "failed", "duplicate-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "failed", "deleted-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "duplicate", "duplicate-only-request")).toBeVisible();
    await expect(row(page, "on-hold", "duplicate", "duplicate-only-request")).toContainText("Duplicate");
    await expect(row(page, "on-hold", "duplicate", "paused-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "duplicate", "failed-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "duplicate", "deleted-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "deleted", "deleted-only-request")).toBeVisible();
    await expect(row(page, "on-hold", "deleted", "deleted-only-request")).toContainText("Deleted");
    await expect(row(page, "on-hold", "deleted", "paused-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "deleted", "failed-only-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "deleted", "duplicate-only-request")).toHaveCount(0);
  });
  test("duplicate confirmation locks catalog rows until original request is terminal", async ({
    page
  }) => {
    const processingApi = await boot(page, "/on-hold", baseState({
      records: [record({
        id: "duplicate-book",
        name: "Duplicate Candidate"
      }), record({
        id: "original-book",
        name: "Original Candidate",
        bookCreationState: "processing"
      })],
      requests: [request({
        id: "duplicate-request",
        bookRecordId: "duplicate-book",
        state: "duplicate",
        duplicateOfRequestId: "original-request",
        duplicateOfRecordId: "original-book"
      }), request({
        id: "original-request",
        bookRecordId: "original-book",
        state: "processing"
      })],
      ui: {
        actionDelayMs: 80,
        pipelineDelayMs: 20_000
      }
    }));
    await checkbox(page, "on-hold", "duplicate", "duplicate-request").check();
    await page.getByTestId("on-hold-duplicate-duplicate-btn").click();
    await expect(row(page, "on-hold", "duplicate", "duplicate-request")).toContainText("Confirmed duplicate");
    await page.goto("/catalog");
    await expect(checkbox(page, "catalog", "records", "duplicate-book")).toBeDisabled();
    processingApi.updateRequest("original-request", {
      state: "failed"
    });
    await page.reload();
    await expect(checkbox(page, "catalog", "records", "duplicate-book")).toBeEnabled();
  });
  test("incomplete page automation, read-only records, and completed-book actions", async ({
    page
  }) => {
    await boot(page, "/incomplete", baseState({
      records: [record({
        id: "incomplete-book",
        name: "Incomplete Book",
        category: "Incomplete",
        writer: "Missing Writer",
        wasIncomplete: true,
        willResolveToCategory: "Novel"
      }), record({
        id: "completed-book",
        name: "Resolved Book",
        category: "Novel",
        writer: "Done Writer",
        wasIncomplete: true,
        resolvedFromIncomplete: true,
        bookCreationState: "created"
      })],
      requests: [request({
        id: "completed-request",
        bookRecordId: "completed-book",
        state: "created"
      })],
      ui: {
        actionDelayMs: 80,
        pipelineDelayMs: 2_000
      }
    }));
    await expect(page.getByTestId("incomplete-overview-stat-incomplete")).toContainText("1");
    await expect(page.getByTestId("incomplete-overview-stat-resolved")).toContainText("1");
    await expect(row(page, "incomplete", "records", "incomplete-book")).toBeVisible();
    await expect(page.getByTestId("incomplete-records-table")).toBeVisible();
    await expect(page.locator('[data-testid="incomplete-records-table"] thead')).toContainText("Name");
    await expect(page.locator('[data-testid="incomplete-records-table"] thead')).toContainText("URL");
    await expect(page.locator('[data-testid="incomplete-records-table"] thead')).not.toContainText("Book");
    await expect(page.locator('[data-testid="incomplete-records-table"] tbody tr').first()).toContainText("https://example.test/books/reusable-systems");
    await expect(page.getByTestId("incomplete-automation-interval")).toHaveValue("weekly");
    await expect(page.getByTestId("incomplete-automation-time")).toHaveValue("03:00");
    await expect(page.getByTestId("incomplete-automation-status")).toHaveCount(0);
    expect(await automationControlHeights(page, "incomplete")).toEqual({
      button: 30,
      toggle: 30
    });
    await expect(page.getByTestId("incomplete-records-select-all")).toHaveCount(0);
    await expect(page.getByTestId("incomplete-records-select-incomplete-book")).toHaveCount(0);
    await expect(page.getByTestId("incomplete-records-recreate-btn")).toHaveCount(0);
    await page.getByTestId("incomplete-records-search").fill("missing writer");
    await expectVisibleCount(page, "incomplete", "records", 1);
    await openCardFilters(page, "incomplete", "records");
    await page.getByTestId("incomplete-records-category-filter").selectOption("Incomplete");
    await expect(page.getByTestId("incomplete-records-active-filters")).toContainText("Incomplete");
    await page.getByTestId("incomplete-automation-enabled").check();
    await page.getByTestId("incomplete-automation-save-btn").click();
    await expect(page.getByTestId("incomplete-automation-status")).toContainText("Saved");
    await page.getByTestId("incomplete-automation-run-btn").click();
    await expect(page.getByTestId("incomplete-automation-run-btn")).toHaveAttribute("data-state", "syncing");
    await expect(row(page, "incomplete", "completed", "request-incomplete-book")).toBeVisible();
    await expect(page.getByTestId("incomplete-overview-stat-incomplete")).toContainText("0");
    await checkbox(page, "incomplete", "completed", "completed-request").check();
    await page.getByTestId("incomplete-completed-recreate-btn").click();
    await expect(page.getByTestId("incomplete-completed-loader")).toBeVisible();
    await expect(row(page, "incomplete", "completed", "completed-request")).toHaveCount(0);
    await page.goto("/create");
    await expect(row(page, "create", "requests", "completed-request")).toBeVisible();
    await page.goto("/incomplete");
    await checkbox(page, "incomplete", "completed", "request-incomplete-book").check();
    await page.getByTestId("incomplete-completed-delete-btn").click();
    await expect(page.getByTestId("incomplete-completed-loader")).toBeVisible();
    await expect(row(page, "incomplete", "completed", "request-incomplete-book")).toHaveCount(0);
    await page.goto("/on-hold");
    await expect(row(page, "on-hold", "deleted", "request-incomplete-book")).toBeVisible();
  });
  test("incomplete automation exposes resume after pausing", async ({
    page
  }) => {
    await boot(page, "/incomplete", baseState({
      sync: {
        ...baseState().sync,
        status: "paused",
        runMode: SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
        fetchedCount: 6,
        progress: {
          runMode: SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
          savedData: {
            runMode: SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            nextPageIndex: 1,
            fetchedCount: 6
          }
        },
        message: "Saved progress for 6 records before pausing."
      }
    }));
    await expect(page.getByTestId("incomplete-automation-run-btn")).toHaveAttribute("data-state", "paused");
    await expect(page.getByTestId("incomplete-automation-run-btn")).toHaveAttribute("aria-label", "Resume incomplete catalog sync");
    await page.getByTestId("incomplete-automation-run-btn").click();
    await expect(page.getByTestId("incomplete-automation-run-btn")).toHaveAttribute("data-state", "syncing");
    await expect(page.getByTestId("incomplete-automation-status")).toContainText("Restarting incomplete catalog sync from the beginning.");
  });
});

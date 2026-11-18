import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("manual start from paused automated request creation preserves the phase-two checkpoint", async ({
    page
  }) => {
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "carry-a",
        name: "Carry A",
        bookCreationState: "created"
      }), record({
        id: "carry-b",
        name: "Carry B",
        updatedAt: iso(24)
      })],
      requests: [request({
        id: "request-carry-a",
        bookRecordId: "carry-a",
        state: "created"
      })],
      sync: {
        ...baseState().sync,
        status: "paused",
        phase: "request_creation",
        runMode: SYNC_RUN_MODE_CATALOG_AUTOMATION,
        remotePages: [[record({
          id: "carry-b",
          name: "Carry B",
          updatedAt: iso(24)
        })], []],
        pageIndex: 1,
        fetchedCount: 1,
        progress: {
          runMode: SYNC_RUN_MODE_CATALOG_AUTOMATION,
          phase: "request_creation",
          phaseStatuses: {
            sync: "completed",
            request_creation: "paused"
          },
          savedData: {
            runMode: SYNC_RUN_MODE_CATALOG_AUTOMATION,
            nextPageIndex: 1,
            fetchedCount: 1,
            sessionId: "catalog-session-9",
            checkpointToken: "catalog-session-9:0:1:1"
          },
          requestCreation: {
            baseCheckpointToken: "catalog-session-9:0:1:1",
            lastRecordId: "carry-a",
            processedCount: 1,
            createdCount: 1,
            unsupportedCount: 0
          }
        },
        message: "Saved request creation progress after scanning 1 record."
      },
      automation: {
        ...baseState().automation,
        catalog: {
          ...baseState().automation.catalog,
          statusMessage: "Saved request creation progress after scanning 1 record."
        }
      },
      ui: {
        ...baseState().ui,
        syncDelayMs: 120,
        pipelineDelayMs: 120
      }
    }));
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeEnabled();
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("aria-label", "Resume automated request creation");
    await page.getByTestId("catalog-sync-start-btn").click();
    await expect(page.getByTestId("catalog-sync-progress")).toContainText("Sync complete.");
    await expect(page.getByTestId("catalog-sync-progress")).not.toContainText("Continuing catalog sync from the saved endpoint.");
    await expect(page.getByTestId("catalog-sync-loader")).toHaveCount(0);
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("aria-label", "Resume automated request creation");
    await page.getByTestId("catalog-automation-run-btn").click();
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Resuming automated request creation from saved progress.");
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Created 1 request");
    await page.goto("/create");
    await expect(row(page, "create", "created", "request-carry-a")).toBeVisible();
    await expect(row(page, "create", "created", "request-carry-b")).toBeVisible();
  });
  test("create cards show only status-scoped rows and remove the details column", async ({
    page
  }) => {
    await boot(page, "/create", baseState({
      records: [record({
        id: "initial-only",
        name: "Initial Only",
        category: "Poetry"
      }), record({
        id: "queued-only",
        name: "Queued Only",
        category: "Science"
      }), record({
        id: "processing-only",
        name: "Processing Only",
        category: "Drama"
      }), record({
        id: "created-only",
        name: "Created Only",
        category: "History"
      })],
      requests: [request({
        id: "initial-only-request",
        bookRecordId: "initial-only",
        state: "initial"
      }), request({
        id: "queued-only-request",
        bookRecordId: "queued-only",
        state: "queued"
      }), request({
        id: "processing-only-request",
        bookRecordId: "processing-only",
        state: "processing"
      }), request({
        id: "created-only-request",
        bookRecordId: "created-only",
        state: "created",
        linkedBookId: "created-only-book-id",
        linkedBookSlug: "created-only-book"
      })],
      ui: {
        ...baseState().ui,
        pipelineDelayMs: 60_000
      }
    }));
    for (const cardId of ["requests", "queue", "processing"]) {
      await expect(page.getByTestId(`create-${cardId}-table`).getByRole("columnheader", {
        name: "Details"
      })).toHaveCount(0);
      await expect(page.getByTestId(`create-${cardId}-table`).locator("thead th")).toHaveCount(6);
    }
    await expect(page.getByTestId("create-created-table").getByRole("columnheader", {
      name: "Details"
    })).toHaveCount(0);
    await expect(page.getByTestId("create-created-table").locator("thead th").filter({
      hasText: "Open"
    })).toHaveCount(1);
    await expect(page.getByTestId("create-created-table").locator("thead th")).toHaveCount(7);
    await expectVisibleCount(page, "create", "requests", 1);
    await expectVisibleCount(page, "create", "queue", 1);
    await expectVisibleCount(page, "create", "processing", 1);
    await expectVisibleCount(page, "create", "created", 1);
    await expect(row(page, "create", "requests", "initial-only-request")).toBeVisible();
    await expect(row(page, "create", "requests", "initial-only-request")).toContainText("Initial");
    await expect(row(page, "create", "requests", "initial-only-request").locator(".processing-col-details")).toHaveCount(0);
    await expect(row(page, "create", "requests", "queued-only-request")).toHaveCount(0);
    await expect(row(page, "create", "requests", "processing-only-request")).toHaveCount(0);
    await expect(row(page, "create", "requests", "created-only-request")).toHaveCount(0);
    await expect(row(page, "create", "queue", "queued-only-request")).toBeVisible();
    await expect(row(page, "create", "queue", "queued-only-request")).toContainText("Queued");
    await expect(row(page, "create", "queue", "queued-only-request").locator(".processing-col-details")).toHaveCount(0);
    await expect(row(page, "create", "queue", "initial-only-request")).toHaveCount(0);
    await expect(row(page, "create", "queue", "processing-only-request")).toHaveCount(0);
    await expect(row(page, "create", "queue", "created-only-request")).toHaveCount(0);
    await expect(row(page, "create", "processing", "processing-only-request")).toBeVisible();
    await expect(row(page, "create", "processing", "processing-only-request")).toContainText("Processing");
    await expect(row(page, "create", "processing", "processing-only-request").locator(".processing-col-details")).toHaveCount(0);
    await expect(row(page, "create", "processing", "initial-only-request")).toHaveCount(0);
    await expect(row(page, "create", "processing", "queued-only-request")).toHaveCount(0);
    await expect(row(page, "create", "processing", "created-only-request")).toHaveCount(0);
    await expect(row(page, "create", "created", "created-only-request")).toBeVisible();
    await expect(row(page, "create", "created", "created-only-request")).toContainText("Created");
    await expect(row(page, "create", "created", "created-only-request").locator(".processing-col-details")).toHaveCount(0);
    await expect(row(page, "create", "created", "created-only-request").getByRole("link", {
      name: "Open"
    })).toHaveAttribute("href", "/books/created-only-book");
    await expect(row(page, "create", "created", "initial-only-request")).toHaveCount(0);
    await expect(row(page, "create", "created", "queued-only-request")).toHaveCount(0);
    await expect(row(page, "create", "created", "processing-only-request")).toHaveCount(0);
  });
  test("create card skeleton rows match the visible status-only table structure", async ({
    page
  }) => {
    await boot(page, "/create", baseState({
      records: [record({
        id: "queued-skeleton",
        name: "Queued Skeleton",
        category: "Science"
      })],
      requests: [request({
        id: "queued-skeleton-request",
        bookRecordId: "queued-skeleton",
        state: "queued"
      })],
      ui: {
        ...baseState().ui,
        loadDelayMs: 450,
        pipelineDelayMs: 60_000
      }
    }));
    const queueTable = page.getByTestId("create-queue-table");
    const queueSkeletonRow = page.getByTestId("create-queue-table-skeleton");
    await expect(queueSkeletonRow).toBeVisible();
    await expect(queueTable.getByRole("columnheader", {
      name: "Details"
    })).toHaveCount(0);
    await expect(queueTable.locator("thead th")).toHaveCount(6);
  });
  test("empty create cards keep their empty state after the first load", async ({
    page
  }) => {
    await boot(page, "/create", baseState({
      records: [record({
        id: "initial-lone",
        name: "Initial Lone",
        category: "Reference"
      })],
      requests: [request({
        id: "initial-lone-request",
        bookRecordId: "initial-lone",
        state: "initial"
      })],
      ui: {
        ...baseState().ui,
        loadDelayMs: 450,
        pipelineDelayMs: 20_000
      }
    }));
    const emptyCreatedCell = page.getByTestId("create-created-table").locator("tbody td").filter({
      hasText: "No records."
    });
    await expect(emptyCreatedCell).toBeVisible();
    await expect(page.getByTestId("create-created-table-skeleton")).toHaveCount(0);
    await expect(page.getByTestId("create-created-count").locator(".processing-card-count-skeleton")).toHaveCount(0);
    await page.waitForTimeout(200);
    await expect(emptyCreatedCell).toBeVisible();
    await expect(page.getByTestId("create-created-table-skeleton")).toHaveCount(0);
    await expect(page.getByTestId("create-created-count").locator(".processing-card-count-skeleton")).toHaveCount(0);
  });
});

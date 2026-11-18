import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("automated catalog sync creates eligible requests and auto-advances them", async ({
    page
  }) => {
    const records = [record({
      id: "auto-new",
      name: "Auto New",
      bookCreationState: "not_created"
    }), record({
      id: "auto-failed",
      name: "Auto Failed",
      bookCreationState: "failed"
    }), record({
      id: "auto-deleted",
      name: "Auto Deleted",
      bookCreationState: "deleted"
    }), record({
      id: "auto-created",
      name: "Auto Created",
      bookCreationState: "created"
    }), record({
      id: "auto-paused",
      name: "Auto Paused",
      bookCreationState: "paused"
    })];
    await boot(page, "/catalog", baseState({
      records,
      requests: [request({
        id: "failed-old",
        bookRecordId: "auto-failed",
        state: "failed"
      }), request({
        id: "deleted-old",
        bookRecordId: "auto-deleted",
        state: "deleted"
      }), request({
        id: "created-old",
        bookRecordId: "auto-created",
        state: "created"
      }), request({
        id: "paused-old",
        bookRecordId: "auto-paused",
        state: "paused"
      })]
    }));
    await page.getByTestId("catalog-automation-enabled").check();
    await page.getByTestId("catalog-automation-interval").selectOption("weekly");
    await page.getByTestId("catalog-automation-time").fill("04:30");
    await page.getByTestId("catalog-automation-save-btn").click();
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Saved");
    await page.getByTestId("catalog-automation-run-btn").click();
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("data-state", "syncing");
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Created 3 request");
    await page.goto("/create");
    await expect(row(page, "create", "created", "request-auto-new")).toBeVisible();
    await expect(row(page, "create", "requests", "request-auto-new")).toHaveCount(0);
    await expect(row(page, "create", "queue", "request-auto-new")).toHaveCount(0);
    await expect(row(page, "create", "processing", "request-auto-new")).toHaveCount(0);
    await expect(row(page, "create", "created", "request-auto-failed")).toBeVisible();
    await expect(row(page, "create", "created", "request-auto-deleted")).toBeVisible();
    await expect(row(page, "create", "created", "created-old")).toBeVisible();
    await expect(row(page, "create", "paused", "paused-old")).toHaveCount(0);
  });
  test("paused catalog sync allows either card to resume phase one", async ({
    page
  }) => {
    const remainingPage = record({
      id: "resume-remote",
      name: "Resume Remote Book",
      updatedAt: iso(25)
    });
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "resume-a",
        name: "Resume A",
        updatedAt: iso(20)
      }), record({
        id: "resume-b",
        name: "Resume B",
        updatedAt: iso(21)
      }), record({
        id: "resume-c",
        name: "Resume C",
        updatedAt: iso(22)
      })],
      sync: {
        ...baseState().sync,
        status: "paused",
        phase: "sync",
        runMode: SYNC_RUN_MODE_CATALOG_AUTOMATION,
        remotePages: [[], [], [remainingPage], []],
        fetchedCount: 3,
        progress: {
          runMode: SYNC_RUN_MODE_CATALOG_AUTOMATION,
          phase: "sync",
          savedData: {
            runMode: SYNC_RUN_MODE_CATALOG_AUTOMATION,
            nextPageIndex: 2,
            fetchedCount: 3,
            sessionId: "catalog-session-1",
            checkpointToken: "catalog-session-1:0:2:3"
          }
        },
        message: "Sync progress saved. Catalog now has 3 book records."
      }
    }));
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("data-state", "paused");
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("aria-label", "Resume automated catalog sync");
    await expect(page.getByTestId("catalog-sync-resume-btn")).toBeVisible();
    await expect(page.getByTestId("catalog-sync-resume-btn")).toHaveAttribute("data-state", "paused");
    await expect(page.getByTestId("catalog-sync-resume-btn")).toHaveAttribute("aria-label", "Resume sync");
    await expect(page.getByTestId("catalog-sync-resume-btn")).toBeEnabled();
    await page.getByTestId("catalog-automation-run-btn").click();
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("data-state", "syncing");
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Continuing automated catalog sync from the saved endpoint.");
  });
  test("completed sync lets automation start request creation directly", async ({
    page
  }) => {
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "phase-two-direct",
        name: "Phase Two Direct"
      })],
      sync: {
        ...baseState().sync,
        status: "idle",
        phase: "sync",
        runMode: SYNC_RUN_MODE_MANUAL,
        fetchedCount: 1,
        pageIndex: 1,
        progress: {
          runMode: SYNC_RUN_MODE_MANUAL,
          phase: "sync",
          savedData: {
            runMode: SYNC_RUN_MODE_MANUAL,
            nextPageIndex: 1,
            fetchedCount: 1,
            sessionId: "catalog-session-direct-phase-two",
            checkpointToken: "catalog-session-direct-phase-two:0:1:1"
          },
          phaseStatuses: {
            sync: "completed",
            request_creation: "not_started"
          }
        },
        message: "Sync complete. Updated 0, Skipped 0, Added 1."
      },
      ui: {
        ...baseState().ui,
        syncDelayMs: 120,
        pipelineDelayMs: 120
      }
    }));
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeEnabled();
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("aria-label", "Run automated catalog sync");
    await page.getByTestId("catalog-automation-run-btn").click();
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Creating book requests from the synced catalog records.");
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Created 1 request");
  });
});

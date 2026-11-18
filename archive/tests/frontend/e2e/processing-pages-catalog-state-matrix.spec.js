import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("paused catalog sync and paused request creation expose the correct resume controls", async ({
    page
  }) => {
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "dual-paused-a",
        name: "Dual Paused A",
        bookCreationState: "created"
      }), record({
        id: "dual-paused-b",
        name: "Dual Paused B"
      })],
      requests: [request({
        id: "request-dual-paused-a",
        bookRecordId: "dual-paused-a",
        state: "created"
      })],
      sync: {
        ...baseState().sync,
        status: "paused",
        phase: "sync",
        runMode: SYNC_RUN_MODE_MANUAL,
        remotePages: [[record({
          id: "dual-paused-b",
          name: "Dual Paused B"
        })], []],
        pageIndex: 1,
        fetchedCount: 1,
        progress: {
          runMode: SYNC_RUN_MODE_MANUAL,
          phase: "sync",
          phaseStatuses: {
            sync: "paused",
            request_creation: "paused"
          },
          savedData: {
            runMode: SYNC_RUN_MODE_MANUAL,
            nextPageIndex: 1,
            fetchedCount: 1,
            sessionId: "catalog-session-dual-paused",
            checkpointToken: "catalog-session-dual-paused:0:1:1"
          },
          requestCreation: {
            baseCheckpointToken: "catalog-session-dual-paused:0:1:1",
            lastRecordId: "dual-paused-a",
            processedCount: 1,
            createdCount: 1,
            unsupportedCount: 0
          }
        },
        message: "Sync progress saved. Catalog now has 2 book records."
      }
    }));
    await expect(page.getByTestId("catalog-sync-resume-btn")).toHaveAttribute("aria-label", "Resume sync");
    await expect(page.getByTestId("catalog-sync-resume-btn")).toHaveAttribute("data-state", "paused");
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("aria-label", "Resume automated request creation");
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute("data-state", "paused");
  });
  for (const matrixCase of CATALOG_MANUAL_MATRIX_CASES) {
    test(`catalog manual matrix row ${matrixCase.name}`, async ({
      page
    }) => {
      await boot(page, "/catalog", catalogMatrixState(matrixCase.state));
      await expectCatalogManualControl(page, matrixCase.manual.initial);
      await expectCatalogAutomationControl(page, matrixCase.automation.initial);
      if (!matrixCase.manual.after) {
        return;
      }
      await page.getByTestId(matrixCase.manual.initial.testId).click();
      await expectCatalogManualControl(page, matrixCase.manual.after);
      await expectCatalogAutomationControl(page, matrixCase.automation.after);
      await expect(page.getByTestId("catalog-sync-progress")).toContainText(matrixCase.resultMessage);
    });
  }
  for (const matrixCase of CATALOG_AUTOMATION_MATRIX_CASES) {
    test(`catalog automation matrix row ${matrixCase.name}`, async ({
      page
    }) => {
      await boot(page, "/catalog", catalogMatrixState(matrixCase.state));
      await expectCatalogManualControl(page, matrixCase.manual.initial);
      await expectCatalogAutomationControl(page, matrixCase.automation.initial);
      if (!matrixCase.automation.after) {
        return;
      }
      await page.getByTestId("catalog-automation-run-btn").click();
      await expectCatalogManualControl(page, matrixCase.manual.after);
      await expectCatalogAutomationControl(page, matrixCase.automation.after);
      await expect(page.getByTestId("catalog-automation-status")).toContainText(matrixCase.resultMessage);
    });
  }
  test("catalog cards normalize stale record totals against the live overview count", async ({
    page
  }) => {
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "count-a",
        name: "Count A",
        updatedAt: iso(20)
      }), record({
        id: "count-b",
        name: "Count B",
        updatedAt: iso(21)
      }), record({
        id: "count-c",
        name: "Count C",
        updatedAt: iso(22)
      })],
      sync: {
        ...baseState().sync,
        status: "idle",
        phase: "sync",
        message: "Catalog now has 1 book record.",
        progress: {
          runMode: SYNC_RUN_MODE_MANUAL,
          phase: "sync",
          savedData: {
            runMode: SYNC_RUN_MODE_MANUAL,
            nextPageIndex: 3,
            fetchedCount: 3,
            sessionId: "catalog-session-counts",
            checkpointToken: "catalog-session-counts:0:3:3"
          },
          phaseStatuses: {
            sync: "completed",
            request_creation: "not_started"
          }
        }
      },
      automation: {
        ...baseState().automation,
        catalog: {
          ...baseState().automation.catalog,
          statusMessage: "Catalog now has 1 book record."
        }
      }
    }));
    await expect(page.getByTestId("catalog-overview-stat-records")).toContainText("3");
    await expect(page.getByTestId("catalog-sync-progress")).toContainText("Catalog now has 3 book records.");
    await expect(page.getByTestId("catalog-automation-status")).toContainText("Catalog now has 3 book records.");
  });
  test("create, on hold, and incomplete pages use shared processing state for overview cards", async ({
    page
  }) => {
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-initial",
        bookRecordId: "record-1",
        state: "initial"
      }), request({
        id: "req-created",
        bookRecordId: "record-2",
        state: "created"
      }), request({
        id: "req-paused",
        bookRecordId: "record-3",
        state: "paused"
      })],
      records: [record({
        id: "record-1",
        name: "Record One",
        updatedAt: iso(20)
      }), record({
        id: "record-2",
        name: "Record Two",
        updatedAt: iso(21)
      }), record({
        id: "record-3",
        name: "Record Three",
        updatedAt: iso(22),
        wasIncomplete: true,
        resolvedFromIncomplete: false
      })]
    }));
    await expect(page.getByTestId("create-overview-stat-requests")).toContainText("1");
    expect(processingApi.getRequestCount("state")).toBeGreaterThan(0);
    expect(processingApi.getRequestCount("card:create-overview")).toBe(0);
    await page.goto("/on-hold");
    await expect(page.getByTestId("on-hold-overview-stat-paused")).toContainText("1");
    expect(processingApi.getRequestCount("card:on-hold-overview")).toBe(0);
    await page.goto("/incomplete");
    await expect(page.getByTestId("incomplete-overview-stat-incomplete")).toContainText("1");
    expect(processingApi.getRequestCount("card:incomplete-overview")).toBe(0);
    expect(processingApi.getRequestCount("card:incomplete-automation")).toBe(0);
  });
  test("unsupported live updates fall back to polling shared state", async ({
    page
  }) => {
    await page.addInitScript(() => {
      const realSetInterval = window.setInterval.bind(window);
      window.setInterval = (callback, delay, ...args) => realSetInterval(callback, delay >= 15000 ? 25 : delay, ...args);
    });
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-unsupported",
        bookRecordId: "record-1",
        state: "initial"
      })],
      records: [record({
        id: "record-1",
        name: "Record One",
        updatedAt: iso(20)
      })]
    }), {
      eventSourceMode: "unsupported"
    });
    await expect(page.getByTestId("create-stream-status")).toContainText("Live updates are unavailable in this browser.");
    await expect(page.getByTestId("create-overview-stat-requests")).toContainText("1");
    const initialStateRequests = processingApi.getRequestCount("state");
    processingApi.updateRequest("req-unsupported", {
      state: "paused"
    });
    await expect(page.getByTestId("create-overview-stat-requests")).toContainText("0");
    await expect.poll(() => processingApi.getRequestCount("state")).toBeGreaterThan(initialStateRequests);
  });
});

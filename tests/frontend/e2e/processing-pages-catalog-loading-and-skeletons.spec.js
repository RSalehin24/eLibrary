import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("catalog loading cards and controls keep the same dimensions as the loaded UI", async ({
    page
  }) => {
    const initialState = baseState({
      automation: {
        catalog: {
          ...baseState().automation.catalog,
          statusMessage: "Saved."
        },
        incomplete: {
          ...baseState().automation.incomplete
        }
      },
      ui: {
        ...baseState().ui,
        loadDelayMs: 450,
        pipelineDelayMs: 5_000
      }
    });
    await boot(page, "/catalog", initialState);
    await expect(page.getByTestId("catalog-automation-run-skeleton")).toBeVisible();
    await expect(page.getByTestId("catalog-sync-control-skeleton")).toBeVisible();
    const loadingDimensions = await controlDimensions(page, [{
      key: "automationRun",
      testId: "catalog-automation-run-skeleton"
    }, {
      key: "automationToggle",
      testId: "catalog-automation-enabled-skeleton"
    }, {
      key: "automationInterval",
      testId: "catalog-automation-interval-skeleton"
    }, {
      key: "automationTime",
      testId: "catalog-automation-time-skeleton"
    }, {
      key: "automationSave",
      testId: "catalog-automation-save-skeleton"
    }, {
      key: "manualSync",
      testId: "catalog-sync-control-skeleton"
    }, {
      key: "recordsCount",
      testId: "catalog-records-count"
    }, {
      key: "overviewValue",
      selector: '[data-testid="catalog-overview-stat-records"] .processing-value-skeleton'
    }, {
      key: "manualStatus",
      selector: '[data-testid="catalog-sync-card"] .processing-status-skeleton'
    }]);
    await expect(page.getByTestId("catalog-automation-run-btn")).toBeVisible();
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeVisible();
    const loadedDimensions = await controlDimensions(page, [{
      key: "automationRun",
      testId: "catalog-automation-run-btn"
    }, {
      key: "automationToggle",
      testId: "catalog-automation-enabled",
      closest: ".processing-switch"
    }, {
      key: "automationInterval",
      testId: "catalog-automation-interval",
      closest: ".processing-automation-field-control"
    }, {
      key: "automationTime",
      testId: "catalog-automation-time",
      closest: ".processing-automation-field-control"
    }, {
      key: "automationSave",
      testId: "catalog-automation-save-btn"
    }, {
      key: "manualSync",
      testId: "catalog-sync-start-btn"
    }, {
      key: "recordsCount",
      testId: "catalog-records-count"
    }, {
      key: "overviewValue",
      selector: '[data-testid="catalog-overview-stat-records"] strong'
    }, {
      key: "manualStatus",
      testId: "catalog-sync-progress"
    }]);
    expect({
      automationRun: loadingDimensions.automationRun,
      automationToggle: loadingDimensions.automationToggle,
      automationInterval: loadingDimensions.automationInterval,
      automationTime: loadingDimensions.automationTime,
      automationSave: loadingDimensions.automationSave,
      manualSync: loadingDimensions.manualSync,
      recordsCount: loadingDimensions.recordsCount
    }).toEqual({
      automationRun: loadedDimensions.automationRun,
      automationToggle: loadedDimensions.automationToggle,
      automationInterval: loadedDimensions.automationInterval,
      automationTime: loadedDimensions.automationTime,
      automationSave: loadedDimensions.automationSave,
      manualSync: loadedDimensions.manualSync,
      recordsCount: loadedDimensions.recordsCount
    });
    expect(loadingDimensions.overviewValue?.height).toBe(loadedDimensions.overviewValue?.height);
    expect(loadingDimensions.manualStatus?.height).toBe(loadedDimensions.manualStatus?.height);
  });
  test("catalog table skeleton rows keep the same dimensions as loaded rows", async ({
    page
  }) => {
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "catalog-row-size",
        name: "Catalog Row Size",
        category: "Poetry",
        writer: "Row Writer",
        publisher: "Row Publisher"
      })],
      ui: {
        ...baseState().ui,
        loadDelayMs: 450,
        pipelineDelayMs: 5_000
      }
    }));
    await expect(page.getByTestId("catalog-records-table-skeleton")).toBeVisible();
    const loadingRowDimensions = await controlDimensions(page, [{
      key: "row",
      testId: "catalog-records-table-skeleton"
    }]);
    await expect(page.getByTestId("catalog-records-row-catalog-row-size")).toBeVisible();
    const loadedRowDimensions = await controlDimensions(page, [{
      key: "row",
      testId: "catalog-records-row-catalog-row-size"
    }]);
    expect(Math.abs((loadingRowDimensions.row?.height ?? 0) - (loadedRowDimensions.row?.height ?? 0))).toBeLessThanOrEqual(1);
  });
  test("catalog records show bangla source urls as decoded text", async ({
    page
  }) => {
    const encodedUrl = "https://www.example.com/books/%E0%A6%85%E0%A6%97%E0%A7%8D%E0%A6%A8%E0%A6%BF%E0%A6%AA%E0%A6%B0%E0%A7%80%E0%A6%95%E0%A7%8D%E0%A6%B7%E0%A6%BE-%E0%A6%86%E0%A6%B6%E0%A6%BE%E0%A6%AA%E0%A7%82%E0%A6%B0%E0%A7%8D%E0%A6%A3%E0%A6%BE/";
    const decodedUrl = "https://www.example.com/books/অগ্নিপরীক্ষা-আশাপূর্ণা/";
    const encodedFragment = "%E0%A6%85%E0%A6%97%E0%A7%8D%E0%A6%A8%E0%A6%BF%E0%A6%AA%E0%A6%B0";
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "bangla-record",
        name: "অগ্নিপরীক্ষা",
        url: encodedUrl,
        category: "উপন্যাস",
        writer: "আশাপূর্ণা দেবী"
      })]
    }));
    const banglaRow = row(page, "catalog", "records", "bangla-record");
    await expect(banglaRow).toContainText(decodedUrl);
    await expect(banglaRow).not.toContainText(encodedFragment);
  });
  test("manual sync completes automatically without an explicit pause", async ({
    page
  }) => {
    await boot(page, "/catalog", baseState({
      sync: {
        ...baseState().sync,
        remotePages: [[record({
          id: "sync-a",
          name: "Sync A",
          updatedAt: iso(21)
        })], [record({
          id: "sync-b",
          name: "Sync B",
          updatedAt: iso(22)
        })], []]
      },
      ui: {
        ...baseState().ui,
        syncDelayMs: 120,
        pipelineDelayMs: 2_000
      }
    }));
    await page.getByTestId("catalog-sync-start-btn").click();
    await expect(page.getByTestId("catalog-sync-loader")).toBeVisible();
    await expect(page.getByRole("status").filter({
      hasText: "Sync started"
    })).toBeVisible();
    await expect(page.getByTestId("catalog-sync-pause-btn")).toHaveAttribute("data-state", "syncing");
    await expect(row(page, "catalog", "records", "sync-a")).toBeVisible();
    await expect(row(page, "catalog", "records", "sync-b")).toBeVisible();
    await expect(page.getByTestId("catalog-sync-loader")).toHaveCount(0);
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeEnabled();
    await expect(page.getByTestId("catalog-sync-progress")).toContainText("Sync complete");
  });
  test("manual sync does not repost incomplete automation page ids", async ({
    page
  }) => {
    const processingApi = await boot(page, "/catalog", baseState({
      sync: {
        ...baseState().sync,
        message: "Incomplete catalog sync complete. Updated 1 book.",
        remotePages: [["stale-incomplete-record"], []]
      },
      ui: {
        ...baseState().ui,
        syncDelayMs: 5_000
      }
    }));
    await page.getByTestId("catalog-sync-start-btn").click();
    await expect(page.getByTestId("catalog-sync-loader")).toBeVisible();
    expect(processingApi.getLastSyncStartBody()?.remotePages).toBeUndefined();
  });
});

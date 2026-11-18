import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("offscreen create cards wait to fetch rows until they enter view", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 430,
      height: 520
    });
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-initial",
        bookRecordId: "record-1",
        state: "initial"
      }), request({
        id: "req-queued",
        bookRecordId: "record-2",
        state: "queued"
      }), request({
        id: "req-processing",
        bookRecordId: "record-3",
        state: "processing"
      }), request({
        id: "req-created",
        bookRecordId: "record-4",
        state: "created"
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
        updatedAt: iso(22)
      }), record({
        id: "record-4",
        name: "Record Four",
        updatedAt: iso(23)
      })]
    }));
    await expect(page.getByTestId("create-created-count")).toContainText("1");
    expect(processingApi.getRequestCount("table:create-created")).toBe(0);
    processingApi.updateRequest("req-created", {
      updatedAt: iso(99)
    }, ["create-created"]);
    await page.waitForTimeout(150);
    expect(processingApi.getRequestCount("table:create-created")).toBe(0);
    await card(page, "create", "created").scrollIntoViewIfNeeded();
    await expect(row(page, "create", "created", "req-created")).toContainText("Record Four");
    expect(processingApi.getRequestCount("table:create-created")).toBeGreaterThan(0);
  });
  test("visible card version bumps refetch only the changed table card", async ({
    page
  }) => {
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-initial",
        bookRecordId: "record-1",
        state: "initial"
      }), request({
        id: "req-queued",
        bookRecordId: "record-2",
        state: "queued"
      })],
      records: [record({
        id: "record-1",
        name: "Record One",
        updatedAt: iso(20)
      }), record({
        id: "record-2",
        name: "Record Two",
        updatedAt: iso(21)
      })],
      ui: {
        ...baseState().ui,
        pipelineDelayMs: 60_000
      }
    }));
    await expect(row(page, "create", "requests", "req-initial")).toBeVisible();
    await expect(row(page, "create", "queue", "req-queued")).toBeVisible();
    const initialRequestsLoads = processingApi.getRequestCount("table:create-requests");
    const initialQueueLoads = processingApi.getRequestCount("table:create-queue");
    processingApi.updateRequest("req-initial", {
      errorMessage: "Updated row without leaving Requests."
    }, ["create-requests"]);
    await expect.poll(() => processingApi.getRequestCount("table:create-requests")).toBe(initialRequestsLoads + 1);
    await page.waitForTimeout(150);
    expect(processingApi.getRequestCount("table:create-queue")).toBe(initialQueueLoads);
  });
  test("visible cards keep loaded rows during version-driven background refreshes", async ({
    page
  }) => {
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-initial",
        bookRecordId: "record-1",
        state: "initial"
      })],
      records: [record({
        id: "record-1",
        name: "Record One",
        updatedAt: iso(20)
      })],
      ui: {
        ...baseState().ui,
        stateLoadDelayMs: 50,
        tableLoadDelayMs: 400,
        pipelineDelayMs: 60_000
      }
    }));
    await expect(row(page, "create", "requests", "req-initial")).toBeVisible();
    const initialLoads = processingApi.getRequestCount("table:create-requests");
    processingApi.updateRequest("req-initial", {
      state: "paused"
    }, ["create-requests", "create-overview", "on-hold-overview"]);
    await page.waitForTimeout(150);
    await expect(row(page, "create", "requests", "req-initial")).toBeVisible();
    await expect(page.getByTestId("create-requests-table-skeleton")).toHaveCount(0);
    await expect.poll(() => processingApi.getRequestCount("table:create-requests")).toBe(initialLoads + 1);
    await expect(row(page, "create", "requests", "req-initial")).toHaveCount(0);
    await expect(page.getByTestId("create-overview-stat-requests")).toContainText("0");
  });
  test("later equal-version SSE events do not duplicate an action-driven refresh", async ({
    page
  }) => {
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-initial",
        bookRecordId: "record-1",
        state: "initial"
      })],
      records: [record({
        id: "record-1",
        name: "Record One",
        updatedAt: iso(20)
      })],
      ui: {
        ...baseState().ui,
        pipelineDelayMs: 60_000
      }
    }));
    await expect(row(page, "create", "requests", "req-initial")).toBeVisible();
    const initialLoads = processingApi.getRequestCount("table:create-requests");
    await checkbox(page, "create", "requests", "req-initial").check();
    await page.getByTestId("create-requests-delete-btn").click();
    await expect(row(page, "create", "requests", "req-initial")).toHaveCount(0);
    await expect.poll(() => processingApi.getRequestCount("table:create-requests")).toBe(initialLoads + 1);
    const currentVersion = processingApi.getVersion("create-requests");
    await processingApi.emitVersionsPayload({
      eventId: Date.now(),
      versions: {
        "create-requests": currentVersion
      }
    });
    await page.waitForTimeout(150);
    expect(processingApi.getRequestCount("table:create-requests")).toBe(initialLoads + 1);
  });
  test("shared version bumps refetch shared state exactly once", async ({
    page
  }) => {
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-initial",
        bookRecordId: "record-1",
        state: "initial"
      })],
      records: [record({
        id: "record-1",
        name: "Record One",
        updatedAt: iso(20)
      })],
      ui: {
        ...baseState().ui,
        stateLoadDelayMs: 80,
        pipelineDelayMs: 60_000
      }
    }));
    await expect(row(page, "create", "requests", "req-initial")).toBeVisible();
    await page.waitForTimeout(150);
    const initialStateLoads = processingApi.getRequestCount("state");
    await processingApi.emitVersions(["create-overview"]);
    await expect.poll(() => processingApi.getRequestCount("state")).toBe(initialStateLoads + 1);
    await page.waitForTimeout(300);
    expect(processingApi.getRequestCount("state")).toBe(initialStateLoads + 1);
  });
  test("shared version bumps during an in-flight state load are not dropped", async ({
    page
  }) => {
    const processingApi = await boot(page, "/create", baseState({
      requests: [request({
        id: "req-initial",
        bookRecordId: "record-1",
        state: "initial"
      })],
      records: [record({
        id: "record-1",
        name: "Record One",
        updatedAt: iso(20)
      })],
      ui: {
        ...baseState().ui,
        stateLoadDelayMs: 250,
        pipelineDelayMs: 60_000
      }
    }), {
      stateVersionsSnapshotAtRequestStart: true
    });
    await expect.poll(() => processingApi.getRequestCount("state")).toBe(1);
    await processingApi.emitVersions(["create-overview"]);
    await expect.poll(() => processingApi.getRequestCount("state")).toBe(2);
    await expect(row(page, "create", "requests", "req-initial")).toBeVisible();
    await page.waitForTimeout(300);
    expect(processingApi.getRequestCount("state")).toBe(2);
  });
  test("card search, filters, counts, and actions stay scoped to their own cards", async ({
    page
  }) => {
    await boot(page, "/create", baseState({
      records: [record({
        id: "initial-alpha",
        name: "Initial Alpha",
        category: "Poetry"
      }), record({
        id: "initial-beta",
        name: "Initial Beta",
        category: "Science"
      }), record({
        id: "queued-alpha",
        name: "Queued Alpha",
        category: "Poetry"
      }), record({
        id: "queued-beta",
        name: "Queued Beta",
        category: "Science"
      })],
      requests: [request({
        id: "initial-alpha-request",
        bookRecordId: "initial-alpha",
        state: "initial"
      }), request({
        id: "initial-beta-request",
        bookRecordId: "initial-beta",
        state: "initial"
      }), request({
        id: "queued-alpha-request",
        bookRecordId: "queued-alpha",
        state: "queued"
      }), request({
        id: "queued-beta-request",
        bookRecordId: "queued-beta",
        state: "queued"
      })],
      ui: {
        actionDelayMs: 400,
        pipelineDelayMs: 2_000
      }
    }));
    await expectVisibleCount(page, "create", "requests", 2);
    await expectVisibleCount(page, "create", "queue", 2);
    await page.getByTestId("create-requests-search").fill("alpha");
    await expectVisibleCount(page, "create", "requests", 1);
    await expect(row(page, "create", "requests", "initial-alpha-request")).toBeVisible();
    await expect(row(page, "create", "requests", "initial-beta-request")).toHaveCount(0);
    await expectVisibleCount(page, "create", "queue", 2);
    await openCardFilters(page, "create", "queue");
    await page.getByTestId("create-queue-category-filter").selectOption("Science");
    await expect(page.getByTestId("create-queue-active-filters")).toContainText("Science");
    await expectVisibleCount(page, "create", "queue", 1);
    await expect(row(page, "create", "queue", "queued-beta-request")).toBeVisible();
    await expect(row(page, "create", "queue", "queued-alpha-request")).toHaveCount(0);
    await expectVisibleCount(page, "create", "requests", 1);
    await checkbox(page, "create", "queue", "queued-beta-request").check();
    await page.getByTestId("create-queue-delete-btn").click();
    await expect(page.getByTestId("create-queue-loader")).toBeVisible();
    await expect(page.getByTestId("create-requests-search")).toHaveValue("alpha");
    await expectVisibleCount(page, "create", "requests", 1);
    await expect(checkbox(page, "create", "requests", "initial-alpha-request")).toBeEnabled();
    await expect(page.getByTestId("create-queue-loader")).toHaveCount(0);
  });
});

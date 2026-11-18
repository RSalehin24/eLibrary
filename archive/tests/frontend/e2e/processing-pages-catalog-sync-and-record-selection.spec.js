import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("catalog sync, filters, record selection, and request creation", async ({
    page
  }) => {
    const existing = record({
      id: "existing",
      name: "Stable Local Book",
      writer: "Local Writer",
      publisher: "Local Press",
      updatedAt: iso(1)
    });
    const active = record({
      id: "active",
      name: "Locked Processing Book",
      category: "Science",
      writer: "Busy Writer",
      publisher: "Busy Press",
      bookCreationState: "processing"
    });
    const remoteChanged = record({
      id: "existing",
      name: "Stable Local Book Revised",
      writer: "Local Writer",
      publisher: "Local Press",
      updatedAt: iso(10)
    });
    const remoteNew = record({
      id: "new-remote",
      name: "Fresh Remote Book",
      url: "https://example.test/books/fresh-remote",
      category: "Poetry",
      writer: "Remote Writer",
      translator: "Case Translator",
      publisher: "Remote House",
      updatedAt: iso(11)
    });
    await boot(page, "/catalog", baseState({
      records: [active, existing],
      requests: [request({
        id: "active-request",
        bookRecordId: "active",
        state: "processing"
      })],
      sync: {
        ...baseState().sync,
        remotePages: [[remoteChanged], [remoteNew], []]
      },
      ui: {
        ...baseState().ui,
        syncDelayMs: 2_000
      }
    }));
    await expect(page.getByRole("heading", {
      level: 1,
      name: "Catalog"
    })).toBeVisible();
    await expect(page.getByTestId("catalog-overview-stat-records")).toContainText("2");
    await expect(page.getByTestId("catalog-records-table")).toBeVisible();
    await expect(page.locator('[data-testid="catalog-records-table"] thead')).toContainText("Name");
    await expect(page.locator('[data-testid="catalog-records-table"] thead')).toContainText("URL");
    await expect(page.getByTestId("catalog-automation-interval")).toHaveValue("weekly");
    await expect(page.getByTestId("catalog-automation-time")).toHaveValue("03:00");
    await expect(page.getByTestId("catalog-automation-status")).toHaveCount(0);
    expect(await automationControlHeights(page, "catalog")).toEqual({
      button: 30,
      toggle: 30
    });
    await expect(page.locator('[data-testid="catalog-records-table"] tbody tr').first()).toContainText("Stable Local Book");
    await expect(page.getByTestId("catalog-sync-start-btn")).toHaveCSS("width", "58px");
    await expect(page.getByTestId("catalog-sync-start-btn")).toHaveCSS("height", "58px");
    await expect(page.getByTestId("catalog-sync-start-btn")).toHaveCSS("color", "rgb(236, 255, 246)");
    await page.getByTestId("catalog-sync-start-btn").click();
    await expect(page.getByTestId("catalog-sync-loader")).toBeVisible();
    await expect(page.getByTestId("catalog-sync-pause-btn")).toHaveAttribute("data-state", "syncing");
    await page.getByTestId("catalog-sync-pause-btn").click();
    await expect(page.getByTestId("catalog-sync-pause-btn")).toHaveAttribute("data-state", "pausing");
    await expect(page.getByTestId("catalog-sync-resume-btn")).toBeVisible();
    await expect(page.getByTestId("catalog-sync-resume-btn")).toHaveCSS("color", "rgb(236, 255, 246)");
    await expect(page.getByTestId("catalog-sync-loader")).toHaveCount(0);
    await expect(page.getByTestId("catalog-sync-progress")).toContainText("Catalog now has 2 book records");
    await page.getByTestId("catalog-sync-resume-btn").click();
    await expect(row(page, "catalog", "records", "new-remote")).toBeVisible();
    await expect(row(page, "catalog", "records", "existing")).toContainText("Stable Local Book Revised");
    await expect(page.getByTestId("catalog-sync-progress")).toContainText("Skipped 0");
    await expect(page.getByTestId("catalog-sync-progress")).toContainText("Added 1");
    await expect(page.getByTestId("catalog-sync-progress-summary")).toHaveText("Sync complete.");
    await expect(page.getByTestId("catalog-sync-progress-details")).toHaveText("Updated 1, Skipped 0, Added 1.");
    await expect(page.getByTestId("catalog-overview-stat-records")).toContainText("3");
    await page.getByTestId("catalog-records-search").fill("remote writer");
    await expectVisibleCount(page, "catalog", "records", 1);
    await expect(row(page, "catalog", "records", "new-remote")).toBeVisible();
    await page.getByTestId("catalog-records-search").fill("fresh-remote");
    await expectVisibleCount(page, "catalog", "records", 1);
    await page.getByTestId("catalog-records-search").fill("poetry");
    await expectVisibleCount(page, "catalog", "records", 1);
    await page.getByTestId("catalog-records-search").fill("case translator");
    await expectVisibleCount(page, "catalog", "records", 1);
    await page.getByTestId("catalog-records-search").fill("remote house");
    await expectVisibleCount(page, "catalog", "records", 1);
    await page.getByTestId("catalog-records-search").fill("");
    await openCardFilters(page, "catalog", "records");
    await page.getByTestId("catalog-records-category-filter").selectOption("Poetry");
    await expect(page.getByTestId("catalog-records-active-filters")).toContainText("Poetry");
    await expectVisibleCount(page, "catalog", "records", 1);
    await page.getByTestId("catalog-records-status-filter").selectOption("not_created");
    await expect(page.getByTestId("catalog-records-active-filters")).toContainText("Not created");
    await page.getByTestId("catalog-records-category-filter").selectOption("");
    await page.getByTestId("catalog-records-status-filter").selectOption("");
    await expect(checkbox(page, "catalog", "records", "active")).toBeDisabled();
    await checkbox(page, "catalog", "records", "new-remote").check();
    await page.getByTestId("catalog-records-create-btn").click();
    await expect(page.getByTestId("catalog-records-loader")).toBeVisible();
    await expect(page.getByTestId("catalog-records-create-btn")).toBeDisabled();
    await expect(page.getByTestId("catalog-records-loader")).toHaveCount(0);
    await page.goto("/create");
    await expect(page.getByTestId("create-requests-row-request-new-remote").or(page.getByTestId("create-queue-row-request-new-remote")).or(page.getByTestId("create-processing-row-request-new-remote")).or(page.getByTestId("create-created-row-request-new-remote")).first()).toBeVisible();
  });
  test("manual sync pause persists while navigating away from processing routes", async ({
    page
  }) => {
    const remotePaused = record({
      id: "pause-remote",
      name: "Pause Remote Book",
      updatedAt: iso(10)
    });
    await boot(page, "/catalog", baseState({
      sync: {
        ...baseState().sync,
        remotePages: [[remotePaused], []]
      },
      ui: {
        ...baseState().ui,
        syncDelayMs: 2_000
      }
    }));
    await page.getByTestId("catalog-sync-start-btn").click();
    await expect(page.getByTestId("catalog-sync-pause-btn")).toHaveAttribute("data-state", "syncing");
    await page.getByTestId("catalog-sync-pause-btn").click();
    await expect(page.getByTestId("catalog-sync-pause-btn")).toHaveAttribute("data-state", "pausing");
    await page.route("**/api/**", async route => {
      const url = route.request().url();
      if (url.includes("/api/processing/") || url.includes("/api/auth/session/") || url.includes("/api/csrf/") || url.includes("/api/catalog/books/")) {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({})
      });
    });
    await page.getByRole("link", {
      name: "Home",
      exact: true
    }).click();
    await expect(page.getByRole("heading", {
      name: "All Books",
      exact: true
    })).toBeVisible();
    await page.waitForTimeout(4_500);
    await page.getByRole("button", {
      name: "Processing"
    }).click();
    await page.getByRole("link", {
      name: "Catalog",
      exact: true
    }).click();
    await expect(page.getByTestId("catalog-sync-resume-btn")).toBeVisible({
      timeout: 1_200
    });
    await expect(page.getByTestId("catalog-sync-progress")).toContainText("Catalog now has 1 book record", {
      timeout: 1_200
    });
  });
  test("processing cards show skeletons and fetch the next batch after scrolling", async ({
    page
  }) => {
    const records = Array.from({
      length: 95
    }, (_, index) => record({
      id: `scroll-record-${index.toString().padStart(2, "0")}`,
      name: `Scroll Record ${index.toString().padStart(2, "0")}`,
      url: `https://example.test/books/scroll-record-${index.toString().padStart(2, "0")}`,
      category: index % 2 === 0 ? "Poetry" : "Novel"
    }));
    await boot(page, "/catalog", baseState({
      records,
      ui: {
        ...baseState().ui,
        loadDelayMs: 250,
        pipelineDelayMs: 5_000
      }
    }));
    await expect(page.getByTestId("catalog-overview-stat-records").locator(".processing-value-skeleton")).toBeVisible();
    await expect(page.getByTestId("catalog-records-table-skeleton")).toBeVisible();
    await expect.poll(async () => page.getByTestId("catalog-records-table-skeleton").evaluate(row => ({
      rowDisplay: window.getComputedStyle(row).display,
      firstCellDisplay: window.getComputedStyle(row.querySelector("td")).display
    }))).toEqual({
      rowDisplay: "table-row",
      firstCellDisplay: "table-cell"
    });
    await expect(page.getByTestId("catalog-records-row-scroll-record-00")).toBeVisible();
    await expect(page.getByTestId("catalog-records-count")).toContainText("95");
    await expect(page.getByTestId("catalog-records-row-scroll-record-70")).toHaveCount(0);
    await page.getByTestId("catalog-records-row-scroll-record-30").scrollIntoViewIfNeeded();
    await expect(page.getByTestId("catalog-records-load-more-skeleton")).toBeVisible();
    await expect(page.getByTestId("catalog-records-row-scroll-record-70")).toHaveCount(1);
  });
});

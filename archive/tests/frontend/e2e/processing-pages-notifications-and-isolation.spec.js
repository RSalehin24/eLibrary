import { expect, test } from "./support/playwright";
import { PROCESSING_TIMEOUT_MS, SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION, SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE, CATALOG_PHASE_STATUS_NOT_STARTED, CATALOG_PHASE_STATUS_RUNNING, CATALOG_PHASE_STATUS_PAUSING, CATALOG_PHASE_STATUS_PAUSED, CATALOG_PHASE_STATUS_COMPLETED, PROCESSING_CARD_KEYS, INCOMPLETE_CATEGORY_KEYWORDS, sessionPayload, iso, record, request, baseState, mockAuthenticatedSession, clone, categoryIsIncomplete, latestRequestForRecord, requestBlocksSelection, recordSelectable, syncRecordStates, nextRequestId, createRequestForRecord, reconcilePage, nextStateTimestamp, applyRequestTimeouts, requestDetails, decodeUrlForDisplay, rowFromRecord, rowFromRequest, tableRowsForCard, processingSummary, processingCardPayload, filteredTablePayload, finalizeSync, catalogSyncSavedData, catalogSyncCheckpointToken, preserveCatalogRequestCreation, requestCreationBaseCheckpointToken, catalogRequestCreationBaseToken, catalogSavedCheckpointAvailable, catalogPhaseStatuses, catalogPhaseIsActive, explicitCatalogPhaseState, pausedLegacyRequestCreationPhaseState, catalogSummaryPhase, applyCatalogProgress, explicitCatalogPhaseStatus, catalogSyncPhaseStatus, catalogRequestCreationPhaseStatus, catalogRequestCreationCanResume, nextCatalogSessionId, buildCatalogSyncProgress, currentCatalogRequestCreation, buildCatalogRequestCreationProgress, completeCatalogAutomation, syncPauseMessage, startFreshCatalogRun, beginCatalogRequestCreation, resumeCatalogRun, completeIncompleteAutomation, catalogRecordCountMessage, advanceSyncPage, advancePipelineState, mockProcessingApi, boot, row, card, catalogMatrixRequestCreation, catalogMatrixState, expectCatalogManualControl, expectCatalogAutomationControl, CATALOG_MANUAL_MATRIX_CASES, CATALOG_AUTOMATION_MATRIX_CASES, checkbox, automationControlHeights, controlDimensions, openCardFilters, installNotificationAudioSpy, notificationSoundEventCount, expectVisibleCount } from "./processing-pages/index.js";
test.describe("processing pages mocked coverage", () => {
  test("notifications play sounds and profile menu mute suppresses audio while keeping toasts visible", async ({
    page
  }) => {
    await installNotificationAudioSpy(page);
    await boot(page, "/catalog", baseState({
      records: [record({
        id: "sound-record",
        name: "Sound Record"
      }), record({
        id: "failed-record",
        name: "Failed Record"
      })],
      requests: [request({
        id: "failed-request",
        bookRecordId: "failed-record",
        state: "failed",
        errorMessage: "Retry threshold exceeded"
      })],
      ui: {
        ...baseState().ui,
        pipelineDelayMs: 20_000
      }
    }));
    await checkbox(page, "catalog", "records", "sound-record").check();
    await page.getByTestId("catalog-records-create-btn").click();
    await expect(page.getByRole("status").filter({
      hasText: "Requests created"
    })).toBeVisible();
    await expect(page.getByTestId("notification-mute-toggle")).toHaveCount(0);
    const initialSoundCount = await notificationSoundEventCount(page);
    expect(initialSoundCount).toBeGreaterThan(0);
    await page.getByTestId("profile-menu-trigger").click();
    await page.getByTestId("profile-alerts-toggle").click();
    await expect(page.getByTestId("profile-alerts-toggle")).not.toBeChecked();
    await page.getByTestId("catalog-automation-enabled").check();
    await page.getByTestId("catalog-automation-save-btn").click();
    await expect(page.getByRole("status").filter({
      hasText: "Catalog automation saved"
    })).toBeVisible();
    await expect(await notificationSoundEventCount(page)).toBe(initialSoundCount);
  });
  test("card actions stay isolated while separate cards are busy", async ({
    page
  }) => {
    await boot(page, "/on-hold", baseState({
      records: [record({
        id: "failed-book",
        name: "Slow Failed"
      }), record({
        id: "duplicate-book",
        name: "Fast Duplicate"
      })],
      requests: [request({
        id: "failed-request",
        bookRecordId: "failed-book",
        state: "failed",
        errorMessage: "Network retries exhausted"
      }), request({
        id: "duplicate-request",
        bookRecordId: "duplicate-book",
        state: "duplicate"
      })],
      ui: {
        actionDelayMs: 700,
        pipelineDelayMs: 2_000
      }
    }));
    await checkbox(page, "on-hold", "failed", "failed-request").check();
    await page.getByTestId("on-hold-failed-retry-btn").click();
    await expect(page.getByTestId("on-hold-failed-loader")).toBeVisible();
    await expect(checkbox(page, "on-hold", "failed", "failed-request")).toBeDisabled();
    await expect(checkbox(page, "on-hold", "duplicate", "duplicate-request")).toBeEnabled();
    await checkbox(page, "on-hold", "duplicate", "duplicate-request").check();
    await page.getByTestId("on-hold-duplicate-new-btn").click();
    await expect(page.getByTestId("on-hold-duplicate-loader")).toBeVisible();
    await expect(page.getByTestId("on-hold-failed-loader")).toBeVisible();
    await expect(row(page, "on-hold", "duplicate", "duplicate-request")).toHaveCount(0);
    await expect(row(page, "on-hold", "failed", "failed-request")).toHaveCount(0);
  });
  test("processing notifications surface action completion, duplicate detection, and stale failures", async ({
    page
  }) => {
    const processingApi = await boot(page, "/catalog", baseState({
      records: [record({
        id: "toast-record",
        name: "Toast Record"
      }), record({
        id: "duplicate-record",
        name: "Duplicate Record"
      }), record({
        id: "failed-record",
        name: "Failed Record"
      }), record({
        id: "stale-record",
        name: "Stale Record"
      })],
      requests: [request({
        id: "duplicate-processing-request",
        bookRecordId: "duplicate-record",
        state: "initial",
        updatedAt: iso(15),
        pipelineOutcome: "duplicate"
      }), request({
        id: "failed-processing-request",
        bookRecordId: "failed-record",
        state: "processing",
        updatedAt: iso(39),
        pipelineOutcome: "failed"
      }), request({
        id: "stale-processing-request",
        bookRecordId: "stale-record",
        state: "processing",
        updatedAt: iso(5)
      })],
      ui: {
        ...baseState().ui,
        pipelineDelayMs: 120
      }
    }));
    processingApi.setNowIso(iso(40));
    await checkbox(page, "catalog", "records", "toast-record").check();
    await page.getByTestId("catalog-records-create-btn").click();
    await expect(page.getByRole("status").filter({
      hasText: "Requests created"
    })).toBeVisible();
    await page.goto("/on-hold");
    await expect(row(page, "on-hold", "duplicate", "duplicate-processing-request")).toBeVisible();
    await expect(row(page, "on-hold", "failed", "failed-processing-request")).toContainText("Pipeline failed after retries.");
    await expect(row(page, "on-hold", "failed", "stale-processing-request")).toContainText("Processing exceeded 20 minutes without completing.");
  });
});

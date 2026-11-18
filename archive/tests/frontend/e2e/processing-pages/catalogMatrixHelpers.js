import { expect } from "../support/playwright";
import {
  CATALOG_PHASE_STATUS_NOT_STARTED,
  SYNC_RUN_MODE_CATALOG_AUTOMATION,
  SYNC_RUN_MODE_MANUAL,
  baseState,
  record
} from "./fixtures.js";
import { applyCatalogProgress, catalogSyncCheckpointToken } from "./catalogSyncState.js";
export function catalogMatrixRequestCreation({
  sessionId = "catalog-matrix-session",
  nextPageIndex = 1,
  fetchedCount = 1,
  lastRecordId = "matrix-record-1",
  processedCount = 1,
  createdCount = 1,
  unsupportedCount = 0
} = {}) {
  return {
    baseCheckpointToken: catalogSyncCheckpointToken({
      sync: {
        progress: {
          savedData: {
            sessionId,
            nextPageIndex,
            fetchedCount
          }
        }
      }
    }),
    lastRecordId,
    processedCount,
    createdCount,
    unsupportedCount
  };
}
export function catalogMatrixState({
  syncStatus,
  requestCreationStatus,
  topStatus,
  syncOwner = SYNC_RUN_MODE_MANUAL,
  requestCreationOwner = SYNC_RUN_MODE_CATALOG_AUTOMATION,
  nextPageIndex = 1,
  fetchedCount = 1,
  sessionId = "catalog-matrix-session",
  requestCreation = undefined
}) {
  const defaultRequestCreation = requestCreationStatus === CATALOG_PHASE_STATUS_NOT_STARTED ? null : catalogMatrixRequestCreation({
    sessionId,
    nextPageIndex,
    fetchedCount
  });
  const effectiveRequestCreation = requestCreation === undefined ? defaultRequestCreation : requestCreation;
  const syncSavedData = syncStatus === CATALOG_PHASE_STATUS_NOT_STARTED ? null : {
    runMode: syncOwner,
    triggerSource: "button",
    sessionId,
    checkpointToken: `${sessionId}:0:${nextPageIndex}:${fetchedCount}`,
    nextPageIndex,
    fetchedCount
  };
  const state = baseState({
    records: [record({
      id: "matrix-record-1",
      name: "Matrix Record 1"
    })],
    sync: {
      ...baseState().sync,
      status: topStatus,
      runMode: syncOwner,
      pageIndex: nextPageIndex,
      fetchedCount,
      remotePages: [[record({
        id: "matrix-page-1",
        name: "Matrix Page 1"
      })], []]
    },
    ui: {
      ...baseState().ui,
      actionDelayMs: 80,
      syncDelayMs: 60_000,
      pipelineDelayMs: 60_000
    }
  });
  applyCatalogProgress(state, {
    syncStatus,
    syncOwner,
    syncSavedData,
    requestCreationStatus,
    requestCreationOwner,
    requestCreation: effectiveRequestCreation
  });
  state.sync.status = topStatus;
  state.sync.runMode = state.sync.progress?.runMode || syncOwner;
  state.sync.phase = state.sync.progress?.phase || state.sync.phase;
  return state;
}
export async function expectCatalogManualControl(page, expectation) {
  const control = page.getByTestId(expectation.testId);
  await expect(control).toBeVisible();
  await expect(control).toHaveAttribute("aria-label", expectation.label);
  await expect(control).toHaveAttribute("data-state", expectation.state);
  if (expectation.disabled) {
    await expect(control).toBeDisabled();
  } else {
    await expect(control).toBeEnabled();
  }
}
export async function expectCatalogAutomationControl(page, expectation) {
  const control = page.getByTestId("catalog-automation-run-btn");
  await expect(control).toBeVisible();
  await expect(control).toHaveAttribute("aria-label", expectation.label);
  await expect(control).toHaveAttribute("data-state", expectation.state);
  if (expectation.disabled) {
    await expect(control).toBeDisabled();
  } else {
    await expect(control).toBeEnabled();
  }
}

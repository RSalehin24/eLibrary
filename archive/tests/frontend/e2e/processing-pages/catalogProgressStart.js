import {
  CATALOG_PHASE_STATUS_COMPLETED,
  CATALOG_PHASE_STATUS_NOT_STARTED,
  CATALOG_PHASE_STATUS_PAUSED,
  CATALOG_PHASE_STATUS_RUNNING,
  CATALOG_REQUEST_CREATION_PHASE,
  CATALOG_SYNC_PHASE,
  SYNC_RUN_MODE_CATALOG_AUTOMATION,
  SYNC_RUN_MODE_INCOMPLETE_AUTOMATION
} from "./fixtures.js";
import {
  applyCatalogProgress,
  catalogRequestCreationBaseToken,
  catalogRequestCreationPhaseStatus,
  catalogSyncCheckpointToken,
  catalogSyncSavedData,
  explicitCatalogPhaseState,
  nextCatalogSessionId,
  pausedLegacyRequestCreationPhaseState,
  requestCreationBaseCheckpointToken
} from "./catalogSyncState.js";
export function catalogRequestCreationCanResume(state) {
  const requestCreation = explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE)?.requestCreation || state.sync.progress?.requestCreation;
  const checkpointToken = catalogRequestCreationBaseToken(state);
  return state.sync.status === "paused" && catalogRequestCreationPhaseStatus(state) === CATALOG_PHASE_STATUS_PAUSED && requestCreationBaseCheckpointToken(requestCreation) === checkpointToken;
}
export function buildCatalogSyncProgress(state, runMode, {
  savedAt = null,
  syncPhaseStatus = CATALOG_PHASE_STATUS_RUNNING,
  requestCreationPhaseState = null,
  sessionId = null
} = {}) {
  const savedData = {
    runMode,
    fetchedCount: state.sync.fetchedCount,
    nextPageIndex: state.sync.pageIndex,
    sessionId: sessionId || nextCatalogSessionId(state)
  };
  savedData.checkpointToken = `${savedData.sessionId}:0:${savedData.nextPageIndex}:${savedData.fetchedCount}`;
  const preservedRequestCreationPhaseState = requestCreationPhaseState || explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE) || pausedLegacyRequestCreationPhaseState(state);
  const requestCreationStatus = preservedRequestCreationPhaseState?.status === CATALOG_PHASE_STATUS_PAUSED ? CATALOG_PHASE_STATUS_PAUSED : CATALOG_PHASE_STATUS_NOT_STARTED;
  const requestCreation = requestCreationStatus === CATALOG_PHASE_STATUS_PAUSED ? preservedRequestCreationPhaseState.requestCreation : null;
  applyCatalogProgress(state, {
    syncStatus: syncPhaseStatus,
    syncOwner: runMode,
    syncSavedData: savedData,
    syncSavedAt: savedAt,
    requestCreationStatus,
    requestCreation,
    requestCreationOwner: preservedRequestCreationPhaseState?.owner || SYNC_RUN_MODE_CATALOG_AUTOMATION,
    requestCreationSavedAt: preservedRequestCreationPhaseState?.savedAt || null
  });
  return state.sync.progress;
}
export function currentCatalogRequestCreation(state) {
  const savedData = catalogSyncSavedData(state);
  const requestCreationPhaseState = explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE);
  const requestCreation = requestCreationPhaseState?.requestCreation || state.sync.progress?.requestCreation;
  const checkpointToken = catalogRequestCreationBaseToken(state);
  if (checkpointToken && requestCreationBaseCheckpointToken(requestCreation) === checkpointToken) {
    return requestCreation;
  }
  return {
    baseCheckpointToken: checkpointToken || requestCreationBaseCheckpointToken(requestCreation) || savedData.checkpointToken || catalogSyncCheckpointToken(state),
    lastRecordId: "",
    processedCount: 0,
    createdCount: 0,
    unsupportedCount: 0
  };
}
export function buildCatalogRequestCreationProgress(state, requestCreation, {
  savedAt = null,
  syncPhaseState = null,
  requestCreationPhaseStatus = savedAt ? CATALOG_PHASE_STATUS_PAUSED : CATALOG_PHASE_STATUS_RUNNING
} = {}) {
  const currentSyncPhaseState = syncPhaseState || explicitCatalogPhaseState(state, CATALOG_SYNC_PHASE);
  const syncSavedData = currentSyncPhaseState?.savedData || {
    ...catalogSyncSavedData(state),
    runMode: currentSyncPhaseState?.owner || state.sync.runMode || SYNC_RUN_MODE_CATALOG_AUTOMATION
  };
  applyCatalogProgress(state, {
    syncStatus: currentSyncPhaseState?.status || CATALOG_PHASE_STATUS_COMPLETED,
    syncOwner: currentSyncPhaseState?.owner || state.sync.runMode || SYNC_RUN_MODE_CATALOG_AUTOMATION,
    syncSavedData,
    requestCreationStatus: requestCreationPhaseStatus,
    requestCreationOwner: SYNC_RUN_MODE_CATALOG_AUTOMATION,
    requestCreation,
    requestCreationSavedAt: savedAt
  });
  return state.sync.progress;
}
export function completeCatalogAutomation(state, requestCreation = currentCatalogRequestCreation(state)) {
  state.automation.catalog.statusMessage = `Created ${requestCreation.createdCount} requests.`;
  const currentSyncPhaseState = explicitCatalogPhaseState(state, CATALOG_SYNC_PHASE);
  const syncStatus = currentSyncPhaseState?.status === CATALOG_PHASE_STATUS_PAUSED ? CATALOG_PHASE_STATUS_PAUSED : CATALOG_PHASE_STATUS_COMPLETED;
  state.sync.status = syncStatus === CATALOG_PHASE_STATUS_PAUSED ? "paused" : "idle";
  applyCatalogProgress(state, {
    syncStatus,
    syncOwner: currentSyncPhaseState?.owner || state.sync.runMode || SYNC_RUN_MODE_CATALOG_AUTOMATION,
    syncSavedData: currentSyncPhaseState?.savedData || catalogSyncSavedData(state),
    requestCreationStatus: CATALOG_PHASE_STATUS_COMPLETED,
    requestCreationOwner: SYNC_RUN_MODE_CATALOG_AUTOMATION
  });
  state.sync.runMode = state.sync.progress.phase === CATALOG_REQUEST_CREATION_PHASE ? SYNC_RUN_MODE_CATALOG_AUTOMATION : currentSyncPhaseState?.owner || state.sync.runMode || SYNC_RUN_MODE_CATALOG_AUTOMATION;
  state.sync.message = `Automated catalog sync complete. Updated ${state.sync.updatedCount}, Skipped ${state.sync.skippedCount}, Added ${state.sync.appendedCount}.`;
}
export function syncPauseMessage(runMode, phase = "sync") {
  if (phase === "request_creation") {
    return "Pausing automated request creation after the current batch finishes.";
  }
  if (runMode === SYNC_RUN_MODE_CATALOG_AUTOMATION) {
    return "Pausing automated catalog sync after the current page finishes.";
  }
  if (runMode === SYNC_RUN_MODE_INCOMPLETE_AUTOMATION) {
    return "Pausing incomplete catalog sync after the current batch finishes.";
  }
  return "Pausing after the current page finishes.";
}
export function startFreshCatalogRun(state, runMode, {
  remotePages
} = {}) {
  state.sync = {
    ...state.sync,
    ...(remotePages ? {
      remotePages
    } : {}),
    status: "syncing",
    fetchedCount: 0,
    skippedCount: 0,
    updatedCount: 0,
    appendedCount: 0,
    pageIndex: 0,
    runMode,
    phase: CATALOG_SYNC_PHASE
  };
  buildCatalogSyncProgress(state, runMode, {
    sessionId: nextCatalogSessionId(state, {
      reuseCurrent: false
    })
  });
  state.sync.message = runMode === SYNC_RUN_MODE_CATALOG_AUTOMATION ? "Automated catalog sync is running." : "Syncing catalog records.";
}

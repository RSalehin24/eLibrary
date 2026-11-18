import {
  CATALOG_PHASE_STATUS_COMPLETED,
  CATALOG_PHASE_STATUS_NOT_STARTED,
  CATALOG_PHASE_STATUS_PAUSED,
  CATALOG_PHASE_STATUS_PAUSING,
  CATALOG_PHASE_STATUS_RUNNING,
  CATALOG_REQUEST_CREATION_PHASE,
  CATALOG_SYNC_PHASE,
  SYNC_RUN_MODE_CATALOG_AUTOMATION,
  SYNC_RUN_MODE_MANUAL
} from "./fixtures.js";

export function nextCatalogSessionId(state, { reuseCurrent = true } = {}) {
  if (reuseCurrent && state.sync.progress?.savedData?.sessionId) {
    return state.sync.progress.savedData.sessionId;
  }
  state.ui = {
    ...state.ui,
    catalogSessionCount: (state.ui?.catalogSessionCount || 0) + 1
  };
  return `catalog-session-${state.ui.catalogSessionCount}`;
}

export function finalizeSync(state) {
  state.sync.status = "idle";
  state.sync.phase = CATALOG_SYNC_PHASE;
  const savedData = {
    runMode: SYNC_RUN_MODE_MANUAL,
    fetchedCount: state.sync.fetchedCount,
    nextPageIndex: state.sync.pageIndex,
    sessionId: nextCatalogSessionId(state)
  };
  savedData.checkpointToken = `${savedData.sessionId}:0:${savedData.nextPageIndex}:${savedData.fetchedCount}`;
  const preservedRequestCreationPhaseState =
    explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE) ||
    pausedLegacyRequestCreationPhaseState(state);
  const requestCreationStatus =
    preservedRequestCreationPhaseState?.status === CATALOG_PHASE_STATUS_PAUSED
      ? CATALOG_PHASE_STATUS_PAUSED
      : CATALOG_PHASE_STATUS_NOT_STARTED;
  applyCatalogProgress(state, {
    syncStatus: CATALOG_PHASE_STATUS_COMPLETED,
    syncOwner: SYNC_RUN_MODE_MANUAL,
    syncSavedData: savedData,
    requestCreationStatus,
    requestCreationOwner:
      preservedRequestCreationPhaseState?.owner || SYNC_RUN_MODE_CATALOG_AUTOMATION,
    requestCreation:
      requestCreationStatus === CATALOG_PHASE_STATUS_PAUSED
        ? preservedRequestCreationPhaseState.requestCreation
        : null,
    requestCreationSavedAt: preservedRequestCreationPhaseState?.savedAt || null
  });
  state.sync.message = `Sync complete. Updated ${state.sync.updatedCount}, Skipped ${state.sync.skippedCount}, Added ${state.sync.appendedCount}.`;
  state.sync.runMode = SYNC_RUN_MODE_MANUAL;
}
export function catalogSyncSavedData(state) {
  return state.sync.progress?.savedData || {};
}
export function catalogSyncCheckpointToken(state) {
  const savedData = catalogSyncSavedData(state);
  if (!savedData.sessionId) {
    return "";
  }
  return savedData.checkpointToken || `${savedData.sessionId}:0:${savedData.nextPageIndex || 0}:${savedData.fetchedCount || 0}`;
}
export function preserveCatalogRequestCreation(state, checkpointToken) {
  const requestCreation = state.sync.progress?.requestCreation;
  if (requestCreation?.baseCheckpointToken === checkpointToken) {
    return requestCreation;
  }
  return null;
}
export function requestCreationBaseCheckpointToken(requestCreation) {
  return String(requestCreation?.baseCheckpointToken || "").trim();
}
export function catalogRequestCreationBaseToken(state) {
  const requestCreationPhaseState = explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE);
  const requestCreation = requestCreationPhaseState?.requestCreation || state.sync.progress?.requestCreation;
  return String(requestCreationPhaseState?.baseSyncCheckpointToken || "").trim() || requestCreationBaseCheckpointToken(requestCreation);
}
export function catalogSavedCheckpointAvailable(state) {
  return Object.keys(catalogSyncSavedData(state)).length > 0;
}
export function catalogPhaseStatuses(syncStatus = CATALOG_PHASE_STATUS_NOT_STARTED, requestCreationStatus = CATALOG_PHASE_STATUS_NOT_STARTED) {
  const summarize = status => status === CATALOG_PHASE_STATUS_PAUSING ? CATALOG_PHASE_STATUS_RUNNING : status;
  return {
    [CATALOG_SYNC_PHASE]: summarize(syncStatus),
    [CATALOG_REQUEST_CREATION_PHASE]: summarize(requestCreationStatus)
  };
}
export function catalogPhaseIsActive(status) {
  return status === CATALOG_PHASE_STATUS_RUNNING || status === CATALOG_PHASE_STATUS_PAUSING;
}
export function explicitCatalogPhaseState(state, phase) {
  const phaseStates = state.sync.progress?.phaseStates;
  if (phaseStates && typeof phaseStates[phase] === "object") {
    return phaseStates[phase];
  }
  return null;
}
export function pausedLegacyRequestCreationPhaseState(state) {
  if (catalogRequestCreationPhaseStatus(state) !== CATALOG_PHASE_STATUS_PAUSED) {
    return null;
  }
  const requestCreation = state.sync.progress?.requestCreation;
  if (!requestCreation) {
    return null;
  }
  return {
    status: CATALOG_PHASE_STATUS_PAUSED,
    owner: SYNC_RUN_MODE_CATALOG_AUTOMATION,
    triggerSource: "button",
    checkpoint: `request-${requestCreation.lastRecordId || requestCreation.processedCount || 0}`,
    ...(state.sync.phase === CATALOG_REQUEST_CREATION_PHASE && state.sync.progress?.savedAt ? {
      savedAt: state.sync.progress.savedAt
    } : {}),
    requestCreation,
    baseSyncCheckpointToken: requestCreation.baseCheckpointToken || catalogSyncCheckpointToken(state)
  };
}
export function catalogSummaryPhase(syncStatus, requestCreationStatus, runtimeStatus = "idle") {
  if (catalogPhaseIsActive(requestCreationStatus) && ["syncing", "pausing"].includes(runtimeStatus)) {
    return CATALOG_REQUEST_CREATION_PHASE;
  }
  if ((catalogPhaseIsActive(syncStatus) || syncStatus === CATALOG_PHASE_STATUS_PAUSED) && ["syncing", "pausing"].includes(runtimeStatus)) {
    return CATALOG_SYNC_PHASE;
  }
  if (syncStatus === CATALOG_PHASE_STATUS_PAUSED) {
    return CATALOG_SYNC_PHASE;
  }
  if (requestCreationStatus === CATALOG_PHASE_STATUS_PAUSED) {
    return CATALOG_REQUEST_CREATION_PHASE;
  }
  return CATALOG_SYNC_PHASE;
}
export function applyCatalogProgress(state, {
  syncStatus,
  syncOwner,
  syncSavedData,
  syncSavedAt = null,
  requestCreationStatus,
  requestCreationOwner = SYNC_RUN_MODE_CATALOG_AUTOMATION,
  requestCreation = null,
  requestCreationSavedAt = null
}) {
  const normalizedSyncSavedData = syncStatus === CATALOG_PHASE_STATUS_NOT_STARTED ? null : syncSavedData;
  const requestCreationBaseToken = requestCreation?.baseCheckpointToken || state.sync.progress?.phaseStates?.[CATALOG_REQUEST_CREATION_PHASE]?.baseSyncCheckpointToken || normalizedSyncSavedData?.checkpointToken || "";
  const phaseStates = {
    [CATALOG_SYNC_PHASE]: {
      status: syncStatus,
      owner: syncStatus === CATALOG_PHASE_STATUS_NOT_STARTED ? "" : syncOwner,
      triggerSource: "button",
      ...(syncStatus === CATALOG_PHASE_STATUS_NOT_STARTED ? {} : {
        checkpoint: `page-${normalizedSyncSavedData?.nextPageIndex || state.sync.pageIndex || 0}`,
        ...(syncSavedAt ? {
          savedAt: syncSavedAt
        } : {}),
        savedData: normalizedSyncSavedData
      })
    },
    [CATALOG_REQUEST_CREATION_PHASE]: {
      status: requestCreationStatus,
      owner: requestCreationStatus === CATALOG_PHASE_STATUS_NOT_STARTED ? "" : requestCreationOwner,
      triggerSource: "button",
      ...(requestCreationStatus === CATALOG_PHASE_STATUS_NOT_STARTED ? {} : {
        checkpoint: `request-${requestCreation?.lastRecordId || requestCreation?.processedCount || 0}`,
        ...(requestCreationSavedAt ? {
          savedAt: requestCreationSavedAt
        } : {}),
        ...(requestCreation ? {
          requestCreation
        } : {}),
        ...(requestCreationBaseToken ? {
          baseSyncCheckpointToken: requestCreationBaseToken
        } : {})
      })
    }
  };
  const phase = catalogSummaryPhase(syncStatus, requestCreationStatus, state.sync.status);
  const summaryPhaseState = phaseStates[phase];
  state.sync.progress = {
    runMode: summaryPhaseState.owner || syncOwner || state.sync.runMode || SYNC_RUN_MODE_MANUAL,
    phase,
    phaseStatuses: catalogPhaseStatuses(syncStatus, requestCreationStatus),
    phaseStates,
    ...(summaryPhaseState.checkpoint ? {
      checkpoint: summaryPhaseState.checkpoint
    } : {}),
    ...(summaryPhaseState.savedAt ? {
      savedAt: summaryPhaseState.savedAt
    } : {}),
    ...(normalizedSyncSavedData ? {
      savedData: normalizedSyncSavedData
    } : {}),
    ...(requestCreation ? {
      requestCreation
    } : {})
  };
  state.sync.phase = phase;
}
export function explicitCatalogPhaseStatus(state, phase) {
  const explicitState = explicitCatalogPhaseState(state, phase);
  if (explicitState?.status) {
    return explicitState.status;
  }
  return state.sync.progress?.phaseStatuses?.[phase] || "";
}
export function catalogSyncPhaseStatus(state) {
  const explicit = explicitCatalogPhaseStatus(state, CATALOG_SYNC_PHASE);
  if (explicit) {
    if ((state.sync.phase || state.sync.progress?.phase) === CATALOG_SYNC_PHASE && state.sync.status === "pausing" && explicit === CATALOG_PHASE_STATUS_RUNNING) {
      return CATALOG_PHASE_STATUS_PAUSING;
    }
    if ((state.sync.phase || state.sync.progress?.phase) === CATALOG_SYNC_PHASE && state.sync.status === "paused" && (explicit === CATALOG_PHASE_STATUS_RUNNING || explicit === CATALOG_PHASE_STATUS_PAUSING)) {
      return CATALOG_PHASE_STATUS_PAUSED;
    }
    return explicit;
  }
  if ((state.sync.phase || state.sync.progress?.phase) === CATALOG_REQUEST_CREATION_PHASE) {
    return CATALOG_PHASE_STATUS_COMPLETED;
  }
  if (state.sync.status === "paused") {
    return CATALOG_PHASE_STATUS_PAUSED;
  }
  if (state.sync.status === "pausing") {
    return CATALOG_PHASE_STATUS_PAUSING;
  }
  if (state.sync.status === "syncing") {
    return CATALOG_PHASE_STATUS_RUNNING;
  }
  return catalogSavedCheckpointAvailable(state) ? CATALOG_PHASE_STATUS_COMPLETED : CATALOG_PHASE_STATUS_NOT_STARTED;
}
export function catalogRequestCreationPhaseStatus(state) {
  const explicit = explicitCatalogPhaseStatus(state, CATALOG_REQUEST_CREATION_PHASE);
  if (explicit) {
    if ((state.sync.phase || state.sync.progress?.phase) === CATALOG_REQUEST_CREATION_PHASE && state.sync.status === "pausing" && explicit === CATALOG_PHASE_STATUS_RUNNING) {
      return CATALOG_PHASE_STATUS_PAUSING;
    }
    if ((state.sync.phase || state.sync.progress?.phase) === CATALOG_REQUEST_CREATION_PHASE && state.sync.status === "paused" && (explicit === CATALOG_PHASE_STATUS_RUNNING || explicit === CATALOG_PHASE_STATUS_PAUSING)) {
      return CATALOG_PHASE_STATUS_PAUSED;
    }
    return explicit;
  }
  if ((state.sync.phase || state.sync.progress?.phase) === CATALOG_REQUEST_CREATION_PHASE) {
    if (state.sync.status === "paused") {
      return CATALOG_PHASE_STATUS_PAUSED;
    }
    if (state.sync.status === "pausing") {
      return CATALOG_PHASE_STATUS_PAUSING;
    }
    if (state.sync.status === "syncing") {
      return CATALOG_PHASE_STATUS_RUNNING;
    }
  }
  return CATALOG_PHASE_STATUS_NOT_STARTED;
}

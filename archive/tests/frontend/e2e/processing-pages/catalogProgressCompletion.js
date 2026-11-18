import {
  CATALOG_PHASE_STATUS_COMPLETED,
  CATALOG_PHASE_STATUS_PAUSED,
  CATALOG_PHASE_STATUS_PAUSING,
  CATALOG_REQUEST_CREATION_PHASE,
  CATALOG_SYNC_PHASE,
  SYNC_RUN_MODE_CATALOG_AUTOMATION,
  SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
  SYNC_RUN_MODE_MANUAL,
  iso
} from "./fixtures.js";
import {
  categoryIsIncomplete,
  createRequestForRecord,
  latestRequestForRecord,
  reconcilePage
} from "./stateRows.js";
import {
  catalogRequestCreationBaseToken,
  catalogRequestCreationPhaseStatus,
  catalogSyncCheckpointToken,
  catalogSyncSavedData,
  explicitCatalogPhaseState,
  finalizeSync
} from "./catalogSyncState.js";
import {
  buildCatalogRequestCreationProgress,
  buildCatalogSyncProgress,
  catalogRequestCreationCanResume,
  completeCatalogAutomation,
  currentCatalogRequestCreation
} from "./catalogProgressStart.js";
export function beginCatalogRequestCreation(state) {
  const currentSyncPhaseState = explicitCatalogPhaseState(state, CATALOG_SYNC_PHASE);
  const syncSavedData = currentSyncPhaseState?.savedData || {
    ...catalogSyncSavedData(state),
    runMode: currentSyncPhaseState?.owner || state.sync.runMode || SYNC_RUN_MODE_CATALOG_AUTOMATION
  };
  const syncPhaseState = {
    ...currentSyncPhaseState,
    status: currentSyncPhaseState?.status === CATALOG_PHASE_STATUS_PAUSED ? CATALOG_PHASE_STATUS_PAUSED : CATALOG_PHASE_STATUS_COMPLETED,
    owner: currentSyncPhaseState?.owner || state.sync.runMode || SYNC_RUN_MODE_CATALOG_AUTOMATION,
    savedData: syncSavedData
  };
  state.sync.status = "syncing";
  state.sync.runMode = SYNC_RUN_MODE_CATALOG_AUTOMATION;
  buildCatalogRequestCreationProgress(state, {
    baseCheckpointToken: syncPhaseState.savedData?.checkpointToken || catalogSyncCheckpointToken(state),
    lastRecordId: "",
    processedCount: 0,
    createdCount: 0,
    unsupportedCount: 0
  }, {
    syncPhaseState
  });
  state.sync.message = "Creating book requests from the synced catalog records.";
  state.automation.catalog.statusMessage = state.sync.message;
}
export function resumeCatalogRun(state, runMode) {
  const syncPhaseState = explicitCatalogPhaseState(state, CATALOG_SYNC_PHASE);
  const requestCreationPhaseState = explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE);
  const savedData = catalogSyncSavedData(state);
  const nextPageIndex = savedData.nextPageIndex || 0;
  const fetchedCount = savedData.fetchedCount || 0;
  const shouldResumeRequestCreation = runMode === SYNC_RUN_MODE_CATALOG_AUTOMATION && catalogRequestCreationCanResume(state);
  state.sync = {
    ...state.sync,
    status: "syncing",
    pageIndex: nextPageIndex,
    fetchedCount,
    runMode,
    phase: CATALOG_SYNC_PHASE
  };
  if (shouldResumeRequestCreation) {
    state.sync.runMode = SYNC_RUN_MODE_CATALOG_AUTOMATION;
    buildCatalogRequestCreationProgress(state, currentCatalogRequestCreation(state), {
      syncPhaseState
    });
    state.sync.message = "Resuming automated request creation from saved progress.";
    state.automation.catalog.statusMessage = state.sync.message;
    return;
  }
  buildCatalogSyncProgress(state, runMode, {
    requestCreationPhaseState
  });
  state.sync.message = runMode === SYNC_RUN_MODE_CATALOG_AUTOMATION ? "Continuing automated catalog sync from the saved endpoint." : "Continuing catalog sync from the saved endpoint.";
  if (runMode === SYNC_RUN_MODE_CATALOG_AUTOMATION) {
    state.automation.catalog.statusMessage = state.sync.message;
  }
}
export function completeIncompleteAutomation(state) {
  let resolvedCount = 0;
  for (const recordItem of state.records) {
    if (!categoryIsIncomplete(recordItem.category) || !recordItem.willResolveToCategory || recordItem.resolvedFromIncomplete) {
      continue;
    }
    recordItem.category = recordItem.willResolveToCategory;
    recordItem.wasIncomplete = true;
    recordItem.resolvedFromIncomplete = true;
    const latest = latestRequestForRecord(state, recordItem.id);
    if (latest) {
      latest.state = "created";
    } else {
      createRequestForRecord(state, recordItem.id, "created");
    }
    resolvedCount += 1;
  }
  state.automation.incomplete.statusMessage = `Resolved ${resolvedCount} ${resolvedCount === 1 ? "book" : "books"}.`;
  state.sync.status = "idle";
  state.sync.progress = null;
  state.sync.runMode = SYNC_RUN_MODE_MANUAL;
  state.sync.message = `Incomplete catalog sync complete. Updated ${resolvedCount} ${resolvedCount === 1 ? "book" : "books"}.`;
}
export function catalogRecordCountMessage(state) {
  return `Catalog now has ${state.records.length} ${state.records.length === 1 ? "book record" : "book records"}.`;
}
export function advanceSyncPage(state) {
  if (state.sync.runMode === SYNC_RUN_MODE_INCOMPLETE_AUTOMATION) {
    if (state.sync.status === "pausing") {
      state.sync.status = "paused";
      state.sync.progress = {
        savedAt: iso(99),
        checkpoint: `page-${state.sync.pageIndex}`,
        runMode: SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
        savedData: {
          runMode: SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
          fetchedCount: state.sync.fetchedCount,
          nextPageIndex: state.sync.pageIndex
        }
      };
      state.sync.message = `Saved progress for ${state.sync.fetchedCount} ${state.sync.fetchedCount === 1 ? "record" : "records"} before pausing.`;
      return;
    }
    completeIncompleteAutomation(state);
    return;
  }
  if ((state.sync.phase || state.sync.progress?.phase) === CATALOG_REQUEST_CREATION_PHASE) {
    const requestCreation = currentCatalogRequestCreation(state);
    const batchSize = Math.max(1, state.ui?.catalogRequestBatchSize || 50);
    const batch = [...state.records].sort((left, right) => left.id.localeCompare(right.id)).filter(recordItem => !requestCreation.lastRecordId || recordItem.id > requestCreation.lastRecordId).slice(0, batchSize);
    if (!batch.length) {
      completeCatalogAutomation(state, requestCreation);
      return;
    }
    const nextRequestCreation = {
      ...requestCreation
    };
    for (const recordItem of batch) {
      nextRequestCreation.lastRecordId = recordItem.id;
      nextRequestCreation.processedCount += 1;
      const latest = latestRequestForRecord(state, recordItem.id);
      const latestState = latest?.state || recordItem.bookCreationState;
      if (!latest && recordItem.bookCreationState === "not_created" || ["failed", "deleted"].includes(latestState)) {
        createRequestForRecord(state, recordItem.id);
        nextRequestCreation.createdCount += 1;
      }
    }
    const hasMore = [...state.records].sort((left, right) => left.id.localeCompare(right.id)).some(recordItem => recordItem.id > nextRequestCreation.lastRecordId);
    if (state.sync.status === "pausing") {
      if (!hasMore) {
        completeCatalogAutomation(state, nextRequestCreation);
        return;
      }
      state.sync.status = "paused";
      buildCatalogRequestCreationProgress(state, nextRequestCreation, {
        savedAt: iso(99),
        syncPhaseState: explicitCatalogPhaseState(state, CATALOG_SYNC_PHASE)
      });
      state.sync.message = `Saved request creation progress after scanning ${nextRequestCreation.processedCount} ${nextRequestCreation.processedCount === 1 ? "record" : "records"}.`;
      return;
    }
    if (!hasMore) {
      completeCatalogAutomation(state, nextRequestCreation);
      return;
    }
    buildCatalogRequestCreationProgress(state, nextRequestCreation);
    state.sync.message = `Scanned ${nextRequestCreation.processedCount} catalog ${nextRequestCreation.processedCount === 1 ? "record" : "records"}; created ${nextRequestCreation.createdCount} ${nextRequestCreation.createdCount === 1 ? "request" : "requests"} so far.`;
    return;
  }
  const pageRecords = state.sync.remotePages[state.sync.pageIndex] || [];
  if (!pageRecords.length) {
    if (state.sync.runMode === SYNC_RUN_MODE_CATALOG_AUTOMATION) {
      buildCatalogSyncProgress(state, SYNC_RUN_MODE_CATALOG_AUTOMATION, {
        syncPhaseStatus: CATALOG_PHASE_STATUS_COMPLETED
      });
      beginCatalogRequestCreation(state);
      return;
    }
    finalizeSync(state);
    return;
  }
  reconcilePage(state, pageRecords);
  state.sync.fetchedCount += pageRecords.length;
  state.sync.pageIndex += 1;
  const nextPage = state.sync.remotePages[state.sync.pageIndex] || [];
  if (state.sync.status === "pausing") {
    state.sync.status = "paused";
    buildCatalogSyncProgress(state, state.sync.runMode, {
      savedAt: iso(99),
      syncPhaseStatus: CATALOG_PHASE_STATUS_PAUSED,
      requestCreationPhaseState: explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE)
    });
    state.sync.message = `Sync progress saved. ${catalogRecordCountMessage(state)}`;
    return;
  }
  if (!nextPage.length) {
    if (state.sync.runMode === SYNC_RUN_MODE_CATALOG_AUTOMATION) {
      buildCatalogSyncProgress(state, SYNC_RUN_MODE_CATALOG_AUTOMATION, {
        syncPhaseStatus: CATALOG_PHASE_STATUS_COMPLETED
      });
      beginCatalogRequestCreation(state);
      return;
    }
    finalizeSync(state);
    return;
  }
  buildCatalogSyncProgress(state, state.sync.runMode, {
    requestCreationPhaseState: explicitCatalogPhaseState(state, CATALOG_REQUEST_CREATION_PHASE)
  });
  state.sync.message = catalogRecordCountMessage(state);
}

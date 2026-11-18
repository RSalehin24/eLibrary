import { useEffect, useState } from "react";
import LoadingSpinner from "../../../components/LoadingSpinner";
import { useBookProcessing } from "../BookProcessingStore";
import {
  CATALOG_PHASE_STATUS_PAUSED,
  CATALOG_PHASE_STATUS_PAUSING,
  CATALOG_REQUEST_CREATION_PHASE,
  CATALOG_SYNC_PHASE,
  DEFAULT_SYNC_CARD,
  OPTIMISTIC_SYNC_MAX_MS,
  OPTIMISTIC_SYNC_MIN_MS,
  SYNC_RUN_MODE_MANUAL,
  catalogActivePhase,
  catalogPhaseOwner,
  catalogPhaseStatus,
  catalogRuntimePhase,
  normalizeCatalogCountMessage,
  splitSyncMessage
} from "./processingPageModel";
import { IconOnlyActionButton, IconOnlyActionSkeleton, PauseIcon, PlayIcon, ProcessingStatusSkeleton, StopIcon } from "./processingPagePrimitives";
export function CatalogSyncPanel({
  className = "",
  loading = false,
  sync = DEFAULT_SYNC_CARD,
  recordCount,
  blockedByExternalRuntime = false,
  onOptimisticSyncChange = null
}) {
  const [pauseRequested, setPauseRequested] = useState(false);
  const [optimisticSync, setOptimisticSync] = useState(null);
  const {
    busyCards,
    startCatalogSync,
    pauseCatalogSync,
    resumeCatalogSync
  } = useBookProcessing();
  const syncBusy = Boolean(busyCards["catalog-sync"]);
  const effectiveSync = optimisticSync ? {
    ...sync,
    status: optimisticSync.status,
    message: optimisticSync.message,
    runMode: SYNC_RUN_MODE_MANUAL,
    phase: optimisticSync.phase
  } : sync;
  const syncPhaseStatus = catalogPhaseStatus(effectiveSync, CATALOG_SYNC_PHASE);
  const activePhase = catalogActivePhase(effectiveSync);
  const activePhaseOwner = activePhase ? catalogPhaseOwner(effectiveSync, activePhase) : "";
  const syncPhaseIsActive = activePhase === CATALOG_SYNC_PHASE;
  const requestCreationIsActive = activePhase === CATALOG_REQUEST_CREATION_PHASE;
  const canResumeSync = syncPhaseStatus === CATALOG_PHASE_STATUS_PAUSED;
  const manualOwnsActiveSync = syncPhaseIsActive && activePhaseOwner === SYNC_RUN_MODE_MANUAL;
  const otherModeOwnsRuntime = requestCreationIsActive || syncPhaseIsActive && activePhaseOwner !== SYNC_RUN_MODE_MANUAL;
  const isSyncing = manualOwnsActiveSync;
  const isPausing = manualOwnsActiveSync && (pauseRequested || syncPhaseStatus === CATALOG_PHASE_STATUS_PAUSING || effectiveSync.status === "pausing");
  const statusMessage = normalizeCatalogCountMessage(effectiveSync.message, recordCount);
  const syncMessageLines = splitSyncMessage(statusMessage);
  useEffect(() => {
    if (!isSyncing) {
      setPauseRequested(false);
    }
  }, [isSyncing]);
  useEffect(() => {
    if (!optimisticSync) {
      return undefined;
    }
    if (sync.status === optimisticSync.status && catalogRuntimePhase(sync) === (optimisticSync.phase || CATALOG_SYNC_PHASE)) {
      const elapsed = Date.now() - Number(optimisticSync.startedAt || 0);
      if (elapsed >= OPTIMISTIC_SYNC_MIN_MS) {
        setOptimisticSync(null);
        return undefined;
      }
      const timerId = window.setTimeout(() => {
        setOptimisticSync(null);
      }, OPTIMISTIC_SYNC_MIN_MS - elapsed);
      return () => {
        window.clearTimeout(timerId);
      };
    }
    return undefined;
  }, [optimisticSync, sync.status, sync.phase, sync.progress?.phase]);
  useEffect(() => {
    onOptimisticSyncChange?.(optimisticSync ? {
      ...optimisticSync,
      runMode: SYNC_RUN_MODE_MANUAL
    } : null);
  }, [onOptimisticSyncChange, optimisticSync]);
  useEffect(() => {
    if (!optimisticSync || typeof window === "undefined") {
      return undefined;
    }
    const timerId = window.setTimeout(() => {
      setOptimisticSync(null);
    }, OPTIMISTIC_SYNC_MAX_MS);
    return () => {
      window.clearTimeout(timerId);
    };
  }, [optimisticSync]);
  if (loading) {
    return <section className={`detail-card processing-card processing-card-skeleton processing-replacement-card processing-settings-card${className ? ` ${className}` : ""}`} data-testid="catalog-sync-card">
        <div className="processing-card-head">
          <div className="processing-card-head-meta">
            <h2>Manual</h2>
          </div>
        </div>
        <div className="processing-sync-body">
          <IconOnlyActionSkeleton testId="catalog-sync-control-skeleton" label="Start sync" className="processing-icon-button--manual" />
        </div>
        <div className="processing-card-footer processing-card-footer--sync">
          <div className="processing-card-status processing-card-status--stack">
            <ProcessingStatusSkeleton lines={syncMessageLines.length > 1 ? 2 : 1} variant="sync" />
          </div>
        </div>
      </section>;
  }
  async function handlePauseSync() {
    setPauseRequested(true);
    const result = await runWithOptimisticSync({
      status: "pausing",
      message: "Pausing after the current page finishes.",
      phase: CATALOG_SYNC_PHASE
    }, pauseCatalogSync);
    if (!result) {
      setPauseRequested(false);
    }
    return result;
  }
  async function runWithOptimisticSync(nextOptimisticSync, action) {
    setOptimisticSync({
      ...nextOptimisticSync,
      startedAt: Date.now()
    });
    const result = await action?.();
    if (!result) {
      setOptimisticSync(null);
    }
    return result;
  }
  const control = canResumeSync ? {
    testId: "catalog-sync-resume-btn",
    label: "Resume sync",
    icon: <PlayIcon />,
    state: "paused",
    disabled: syncBusy || otherModeOwnsRuntime || blockedByExternalRuntime,
    onClick: () => runWithOptimisticSync({
      status: "syncing",
      message: "Continuing catalog sync from the saved endpoint.",
      phase: CATALOG_SYNC_PHASE
    }, resumeCatalogSync)
  } : isSyncing ? {
    testId: "catalog-sync-pause-btn",
    label: isPausing ? "Pausing sync" : "Pause sync",
    icon: <PauseIcon />,
    state: isPausing ? "pausing" : "syncing",
    disabled: syncBusy || isPausing,
    onClick: handlePauseSync
  } : {
    testId: "catalog-sync-start-btn",
    label: "Start sync",
    icon: <PlayIcon />,
    state: "idle",
    disabled: syncBusy || otherModeOwnsRuntime || blockedByExternalRuntime,
    onClick: () => runWithOptimisticSync({
      status: "syncing",
      message: "Syncing catalog records.",
      phase: CATALOG_SYNC_PHASE
    }, () => startCatalogSync())
  };
  return <section className={`detail-card processing-card processing-replacement-card processing-settings-card${className ? ` ${className}` : ""}`} data-testid="catalog-sync-card">
      <div className="processing-card-head">
        <div className="processing-card-head-meta">
          <h2>Manual</h2>
        </div>
      </div>
      <div className="processing-sync-body">
        <IconOnlyActionButton testId={control.testId} label={control.label} icon={control.icon} state={control.state} disabled={control.disabled} onClick={control.onClick} className="processing-icon-button--manual" />
      </div>
      <div className="processing-card-footer processing-card-footer--sync">
        <div className="processing-card-status processing-card-status--stack">
          {syncBusy || isSyncing ? <span className="processing-inline-loader" data-testid="catalog-sync-loader">
              <LoadingSpinner size={14} /> {isPausing ? "Pausing" : "Syncing"}
            </span> : null}
          <span className="catalog-toolbar-sync-status" data-testid="catalog-sync-progress">
            {syncMessageLines.map((line, index) => <span key={`${sync.status}-${index}-${line}`} className={`catalog-toolbar-sync-status-line${index === 0 ? " catalog-toolbar-sync-status-line--summary" : " catalog-toolbar-sync-status-line--details"}`} data-testid={index === 0 ? "catalog-sync-progress-summary" : "catalog-sync-progress-details"}>
                {line}
              </span>)}
          </span>
        </div>
      </div>
    </section>;
}

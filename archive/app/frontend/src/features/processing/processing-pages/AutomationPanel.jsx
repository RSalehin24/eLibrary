import { useEffect, useState } from "react";
import AsyncButton from "../../../components/AsyncButton";
import LoadingSpinner from "../../../components/LoadingSpinner";
import {
  CATALOG_PHASE_STATUS_NOT_STARTED,
  CATALOG_PHASE_STATUS_COMPLETED,
  CATALOG_PHASE_STATUS_PAUSED,
  CATALOG_PHASE_STATUS_PAUSING,
  CATALOG_REQUEST_CREATION_PHASE,
  CATALOG_SYNC_PHASE,
  DEFAULT_AUTOMATION_CARD,
  DEFAULT_SYNC_CARD,
  OPTIMISTIC_SYNC_MAX_MS,
  OPTIMISTIC_SYNC_MIN_MS,
  SYNC_RUN_MODE_CATALOG_AUTOMATION,
  SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
  catalogActivePhase,
  catalogPhaseIsActive,
  catalogPhaseOwner,
  catalogPhaseStatus,
  catalogRuntimePhase,
  normalizeCatalogCountMessage
} from "./processingPageModel";
import { AutomationFieldSkeleton, ButtonSkeleton, IconOnlyActionButton, IconOnlyActionSkeleton, PauseIcon, PlayIcon, ProcessingStatusSkeleton, StopIcon, SwitchSkeleton } from "./processingPagePrimitives";
export function AutomationPanel({
  pageId,
  title,
  automation = DEFAULT_AUTOMATION_CARD,
  sync = DEFAULT_SYNC_CARD,
  blockedByExternalRuntime = false,
  onOptimisticSyncChange = null,
  recordCount,
  loading = false,
  saving = false,
  running = false,
  onSave,
  onRun,
  onPause,
  onResume,
  className = ""
}) {
  const [form, setForm] = useState({
    enabled: automation.enabled,
    interval: automation.interval,
    time: automation.time
  });
  const [optimisticSync, setOptimisticSync] = useState(null);
  const [pendingNonCatalogSync, setPendingNonCatalogSync] = useState(null);
  const runMode = pageId === "catalog" ? SYNC_RUN_MODE_CATALOG_AUTOMATION : SYNC_RUN_MODE_INCOMPLETE_AUTOMATION;
  const effectiveSync = optimisticSync ? {
    ...sync,
    status: optimisticSync.status,
    message: optimisticSync.message,
    runMode,
    phase: optimisticSync.phase
  } : sync;
  const displaySync = pageId === "catalog" || !pendingNonCatalogSync ? effectiveSync : {
    ...effectiveSync,
    status: pendingNonCatalogSync.status,
    message: pendingNonCatalogSync.message,
    runMode,
    phase: pendingNonCatalogSync.phase
  };
  const syncPhaseStatus = pageId === "catalog" ? catalogPhaseStatus(displaySync, CATALOG_SYNC_PHASE) : CATALOG_PHASE_STATUS_NOT_STARTED;
  const requestCreationPhaseStatus = pageId === "catalog" ? catalogPhaseStatus(displaySync, CATALOG_REQUEST_CREATION_PHASE) : CATALOG_PHASE_STATUS_NOT_STARTED;
  const activePhase = pageId === "catalog" ? catalogActivePhase(displaySync) : "";
  const activePhaseOwner = pageId === "catalog" && activePhase ? catalogPhaseOwner(displaySync, activePhase) : displaySync.runMode;
  const activePhaseStatus = pageId === "catalog" && activePhase ? catalogPhaseStatus(displaySync, activePhase) : "";
  const hasActiveSync = Boolean(activePhase) && catalogPhaseIsActive(activePhaseStatus);
  const runningCurrentPhase = hasActiveSync && activePhaseOwner === runMode;
  const blockedByOtherRuntime = pageId === "catalog" ? hasActiveSync && activePhaseOwner !== runMode : displaySync.status !== "idle" && displaySync.runMode !== runMode;
  const canResumeRequestCreation = pageId === "catalog" && requestCreationPhaseStatus === CATALOG_PHASE_STATUS_PAUSED;
  const canResumeSyncPhase = pageId === "catalog" ? syncPhaseStatus === CATALOG_PHASE_STATUS_PAUSED : displaySync.status === "paused";
  const pausedActionPhase = pageId === "catalog" ? canResumeRequestCreation ? CATALOG_REQUEST_CREATION_PHASE : canResumeSyncPhase ? CATALOG_SYNC_PHASE : "" : displaySync.status === "paused" ? CATALOG_SYNC_PHASE : "";
  const startsRequestCreationDirectly = pageId === "catalog" && !canResumeRequestCreation && !canResumeSyncPhase && syncPhaseStatus === CATALOG_PHASE_STATUS_COMPLETED && requestCreationPhaseStatus === CATALOG_PHASE_STATUS_NOT_STARTED;
  const actionPhase = pageId === "catalog" ? runningCurrentPhase && activePhase ? activePhase : pausedActionPhase || (startsRequestCreationDirectly ? CATALOG_REQUEST_CREATION_PHASE : CATALOG_SYNC_PHASE) : CATALOG_SYNC_PHASE;
  const isRequestCreationPhase = pageId === "catalog" && actionPhase === CATALOG_REQUEST_CREATION_PHASE;
  const runLabel = isRequestCreationPhase && !startsRequestCreationDirectly ? "automated request creation" : pageId === "catalog" ? "automated catalog sync" : "incomplete catalog sync";
  const runMessage = isRequestCreationPhase ? startsRequestCreationDirectly ? "Creating book requests from the synced catalog records." : "Resuming automated request creation from saved progress." : pageId === "catalog" ? startsRequestCreationDirectly ? "Creating book requests from the synced catalog records." : canResumeSyncPhase ? "Continuing automated catalog sync from the saved endpoint." : "Automated catalog sync is running." : "Incomplete catalog sync is running.";
  const pauseMessage = isRequestCreationPhase ? "Pausing automated request creation after the current batch finishes." : pageId === "catalog" ? "Pausing automated catalog sync after the current page finishes." : "Pausing incomplete catalog sync after the current batch finishes.";
  const resumeMessage = isRequestCreationPhase ? "Resuming automated request creation from saved progress." : pageId === "catalog" ? canResumeSyncPhase ? "Continuing automated catalog sync from the saved endpoint." : "Restarting automated catalog sync from the beginning." : "Restarting incomplete catalog sync from the beginning.";
  const isRunning = pageId === "catalog" ? runningCurrentPhase : displaySync.runMode === runMode && (displaySync.status === "syncing" || displaySync.status === "pausing");
  const isPausing = pageId === "catalog" ? runningCurrentPhase && (activePhaseStatus === CATALOG_PHASE_STATUS_PAUSING || displaySync.status === "pausing") : displaySync.runMode === runMode && displaySync.status === "pausing";
  const isPaused = pageId === "catalog" ? !runningCurrentPhase && Boolean(pausedActionPhase) : displaySync.status === "paused" && displaySync.runMode === runMode;
  const busy = saving || running;
  const controlsDisabled = busy || blockedByOtherRuntime || blockedByExternalRuntime;
  const rawStatusMessage = displaySync.status !== "idle" ? displaySync.message || "" : automation.statusMessage || "";
  const statusMessage = pageId === "catalog" ? normalizeCatalogCountMessage(rawStatusMessage, recordCount) : rawStatusMessage;
  const showFooter = saving || Boolean(statusMessage);
  useEffect(() => {
    setForm({
      enabled: automation.enabled,
      interval: automation.interval,
      time: automation.time
    });
  }, [automation.enabled, automation.interval, automation.time]);
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
      runMode
    } : null);
  }, [onOptimisticSyncChange, optimisticSync, runMode]);
  useEffect(() => {
    if (pageId === "catalog" || !pendingNonCatalogSync || typeof window === "undefined") {
      return undefined;
    }
    const elapsed = Date.now() - Number(pendingNonCatalogSync.startedAt || 0);
    const timerId = window.setTimeout(() => {
      setPendingNonCatalogSync(null);
    }, Math.max(OPTIMISTIC_SYNC_MIN_MS - elapsed, 0));
    return () => {
      window.clearTimeout(timerId);
    };
  }, [pageId, pendingNonCatalogSync]);
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
  async function runWithOptimisticState(nextOptimisticSync, action) {
    if (pageId !== "catalog") {
      setPendingNonCatalogSync({
        ...nextOptimisticSync,
        startedAt: Date.now()
      });
    }
    setOptimisticSync({
      ...nextOptimisticSync,
      startedAt: Date.now()
    });
    const result = await action?.();
    if (!result) {
      setPendingNonCatalogSync(null);
      setOptimisticSync(null);
    }
    return result;
  }
  if (loading) {
    return <section className={`detail-card processing-card processing-card-skeleton processing-replacement-card processing-settings-card${className ? ` ${className}` : ""}`} data-testid={`${pageId}-automation-card`}>
        <div className="processing-card-head processing-card-head--settings">
          <div className="processing-card-head-meta">
            <h2>{title}</h2>
          </div>
          <div className="processing-card-head-controls">
            <IconOnlyActionSkeleton testId={`${pageId}-automation-run-skeleton`} label="Run automation" className="processing-icon-button--automation" />
            <SwitchSkeleton testId={`${pageId}-automation-enabled-skeleton`} />
          </div>
        </div>
        <div className="processing-automation-row">
          <AutomationFieldSkeleton testId={`${pageId}-automation-interval-skeleton`} label="Interval" controlClassName="processing-automation-field-control--select" />
          <AutomationFieldSkeleton testId={`${pageId}-automation-time-skeleton`} label="Time" controlClassName="processing-automation-field-control--time" />
          <div className="processing-automation-save-slot">
            <ButtonSkeleton testId={`${pageId}-automation-save-skeleton`} label="Save" />
          </div>
        </div>
        {showFooter ? <div className="processing-card-footer">
            <div className="processing-card-status">
              <ProcessingStatusSkeleton variant="automation" />
            </div>
          </div> : null}
      </section>;
  }
  const runControl = isPaused ? {
    label: pageId === "catalog" && isRequestCreationPhase ? "Resume automated request creation" : pageId === "catalog" ? "Resume automated catalog sync" : "Resume incomplete catalog sync",
    icon: <PlayIcon />,
    state: "paused",
    disabled: controlsDisabled,
    onClick: () => runWithOptimisticState({
      status: "syncing",
      message: resumeMessage,
      phase: actionPhase
    }, onResume)
  } : isRunning ? {
    label: isPausing ? `Pausing ${runLabel}` : `Pause ${runLabel}`,
    icon: <PauseIcon />,
    state: isPausing ? "pausing" : "syncing",
    disabled: busy || isPausing,
    onClick: () => runWithOptimisticState({
      status: "pausing",
      message: pauseMessage,
      phase: actionPhase
    }, onPause)
  } : {
    label: `Run ${runLabel}`,
    icon: <PlayIcon />,
    state: "idle",
    disabled: busy || blockedByOtherRuntime || blockedByExternalRuntime,
    onClick: () => runWithOptimisticState({
      status: "syncing",
      message: runMessage,
      phase: actionPhase
    }, onRun)
  };
  return <section className={`detail-card processing-card processing-replacement-card processing-settings-card${className ? ` ${className}` : ""}`} data-testid={`${pageId}-automation-card`}>
      <div className="processing-card-head processing-card-head--settings">
        <div className="processing-card-head-meta">
          <h2>{title}</h2>
        </div>
        <div className="processing-card-head-controls">
          <IconOnlyActionButton testId={`${pageId}-automation-run-btn`} label={runControl.label} icon={runControl.icon} state={runControl.state} disabled={runControl.disabled} onClick={runControl.onClick} className="processing-icon-button--automation" />
          <label className="processing-switch">
            <input type="checkbox" checked={form.enabled} disabled={controlsDisabled} onChange={event => setForm(current => ({
            ...current,
            enabled: event.target.checked
          }))} data-testid={`${pageId}-automation-enabled`} />
            <span className="processing-switch-track">
              <span className="processing-switch-state">
                {form.enabled ? "On" : "Off"}
              </span>
              <span className="processing-switch-thumb" />
            </span>
          </label>
        </div>
      </div>
      <div className="processing-automation-row">
        <label className="processing-automation-field">
          <span className="processing-automation-field-label">Interval</span>
          <span className="processing-automation-field-control processing-automation-field-control--select">
            <select className="processing-automation-input" value={form.interval} disabled={controlsDisabled} onChange={event => setForm(current => ({
            ...current,
            interval: event.target.value
          }))} data-testid={`${pageId}-automation-interval`}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="biweekly">Bi-weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </span>
        </label>
        <label className="processing-automation-field">
          <span className="processing-automation-field-label">Time</span>
          <span className="processing-automation-field-control processing-automation-field-control--time">
            <input className="processing-automation-input processing-automation-time-input" type="time" value={form.time} disabled={controlsDisabled} onChange={event => setForm(current => ({
            ...current,
            time: event.target.value
          }))} data-testid={`${pageId}-automation-time`} />
          </span>
        </label>
        <div className="processing-automation-save-slot">
          <AsyncButton type="button" className="primary-button" disabled={controlsDisabled} loading={saving} loadingLabel="Saving" onClick={() => onSave(form)} data-testid={`${pageId}-automation-save-btn`}>
            Save
          </AsyncButton>
        </div>
      </div>
      {showFooter ? <div className="processing-card-footer">
          <div className="processing-card-status">
            {saving ? <span className="processing-inline-loader" data-testid={`${pageId}-automation-loader`}>
                <LoadingSpinner size={14} /> Saving
              </span> : null}
            {statusMessage ? <span className="processing-automation-status" data-testid={`${pageId}-automation-status`}>
                {statusMessage}
              </span> : null}
          </div>
        </div> : null}
    </section>;
}

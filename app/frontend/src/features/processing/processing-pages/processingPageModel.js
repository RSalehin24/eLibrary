import { REQUEST_STATE_LABELS } from "../types";
export const SEARCH_PLACEHOLDER =
  "Search name, URL, category, writer, translator, or publisher";
export const PROCESSING_TABLE_BATCH_SIZE = 60;
export const PROCESSING_TABLE_PREFETCH_TRIGGER = 30;
export const PROCESSING_CARD_VISIBILITY_ROOT_MARGIN = "300px 0px";
export const SYNC_RUN_MODE_MANUAL = "manual";
export const SYNC_RUN_MODE_CATALOG_AUTOMATION = "catalog_automation";
export const SYNC_RUN_MODE_INCOMPLETE_AUTOMATION = "incomplete_automation";
export const CATALOG_SYNC_PHASE = "sync";
export const CATALOG_REQUEST_CREATION_PHASE = "request_creation";
export const CATALOG_PHASE_STATUS_NOT_STARTED = "not_started";
export const CATALOG_PHASE_STATUS_RUNNING = "running";
export const CATALOG_PHASE_STATUS_PAUSING = "pausing";
export const CATALOG_PHASE_STATUS_PAUSED = "paused";
export const CATALOG_PHASE_STATUS_COMPLETED = "completed";
export const OPTIMISTIC_SYNC_MIN_MS = 2_000;
export const OPTIMISTIC_SYNC_MAX_MS = 4_000;
export const INCOMPLETE_CATEGORY_KEYWORDS = [
  "incomplete",
  "unfinished",
  "অসম্পূর্ণ",
  "অসম্পূর্ণ বই",
];
export const DEFAULT_SYNC_CARD = {
  status: "idle",
  runMode: SYNC_RUN_MODE_MANUAL,
  message: "Ready to sync.",
};
export const DEFAULT_AUTOMATION_CARD = {
  enabled: false,
  interval: "weekly",
  time: "03:00",
  saved: false,
  lastRunAt: null,
  statusMessage: "",
};
export function formatDate(value) {
  if (!value) {
    return "Never";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(undefined, {
    timeZone: "Asia/Dhaka",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
export function splitSyncMessage(message) {
  const trimmed = String(message || "").trim();
  if (!trimmed) {
    return [];
  }
  const parts = trimmed.match(/^(.+?[.!?])\s+(.+)$/);
  if (!parts) {
    return [trimmed];
  }
  return [parts[1], parts[2]];
}
export function catalogRecordCountMessage(recordCount) {
  const total = Number.isFinite(recordCount) ? recordCount : 0;
  return `Catalog now has ${total} ${total === 1 ? "book record" : "book records"}.`;
}
export function processingStreamStatusMessage(streamMode) {
  if (streamMode === "reconnecting") {
    return "Live updates reconnecting. Refresh checks continue every 15 seconds.";
  }
  if (streamMode === "unsupported") {
    return "Live updates are unavailable in this browser.";
  }
  return "";
}
export function normalizeCatalogCountMessage(message, recordCount) {
  const trimmed = String(message || "").trim();
  if (!trimmed || !Number.isFinite(recordCount)) {
    return trimmed;
  }
  return trimmed.replace(
    /Catalog now has \d+ book records?\./g,
    catalogRecordCountMessage(recordCount),
  );
}
export function catalogRuntimePhase(sync) {
  return sync?.phase || sync?.progress?.phase || CATALOG_SYNC_PHASE;
}
export function catalogPhaseState(sync, phase) {
  const explicit =
    sync?.progress?.phaseStates &&
    typeof sync.progress.phaseStates[phase] === "object"
      ? sync.progress.phaseStates[phase]
      : null;
  if (explicit) {
    return explicit;
  }
  return null;
}
export function catalogPhaseStatus(sync, phase) {
  const explicitState = catalogPhaseState(sync, phase);
  if (explicitState?.status) {
    return explicitState.status;
  }
  const syncPhase = catalogRuntimePhase(sync);
  const runtimeStatus = sync?.status || "idle";
  const explicit = sync?.progress?.phaseStatuses?.[phase];
  if (explicit) {
    if (phase === syncPhase) {
      if (
        runtimeStatus === "pausing" &&
        explicit === CATALOG_PHASE_STATUS_RUNNING
      ) {
        return CATALOG_PHASE_STATUS_PAUSING;
      }
      if (
        runtimeStatus === "paused" &&
        (explicit === CATALOG_PHASE_STATUS_RUNNING ||
          explicit === CATALOG_PHASE_STATUS_PAUSING)
      ) {
        return CATALOG_PHASE_STATUS_PAUSED;
      }
    }
    return explicit;
  }
  const savedData = sync?.progress?.savedData;
  if (phase === CATALOG_SYNC_PHASE) {
    if (syncPhase === CATALOG_REQUEST_CREATION_PHASE) {
      return CATALOG_PHASE_STATUS_COMPLETED;
    }
    if (runtimeStatus === "paused") {
      return CATALOG_PHASE_STATUS_PAUSED;
    }
    if (runtimeStatus === "pausing") {
      return CATALOG_PHASE_STATUS_PAUSING;
    }
    if (runtimeStatus === "syncing") {
      return CATALOG_PHASE_STATUS_RUNNING;
    }
    return savedData
      ? CATALOG_PHASE_STATUS_COMPLETED
      : CATALOG_PHASE_STATUS_NOT_STARTED;
  }
  if (phase === CATALOG_REQUEST_CREATION_PHASE) {
    if (syncPhase === CATALOG_REQUEST_CREATION_PHASE) {
      if (runtimeStatus === "paused") {
        return CATALOG_PHASE_STATUS_PAUSED;
      }
      if (runtimeStatus === "pausing") {
        return CATALOG_PHASE_STATUS_PAUSING;
      }
      if (runtimeStatus === "syncing") {
        return CATALOG_PHASE_STATUS_RUNNING;
      }
    }
    return CATALOG_PHASE_STATUS_NOT_STARTED;
  }
  return CATALOG_PHASE_STATUS_NOT_STARTED;
}
export function catalogPhaseIsActive(status) {
  return (
    status === CATALOG_PHASE_STATUS_RUNNING ||
    status === CATALOG_PHASE_STATUS_PAUSING
  );
}
export function catalogPhaseOwner(sync, phase) {
  const explicitState = catalogPhaseState(sync, phase);
  if (explicitState?.owner) {
    return explicitState.owner;
  }
  const status = catalogPhaseStatus(sync, phase);
  if (status === CATALOG_PHASE_STATUS_NOT_STARTED) {
    return "";
  }
  if (phase === CATALOG_REQUEST_CREATION_PHASE) {
    return SYNC_RUN_MODE_CATALOG_AUTOMATION;
  }
  const savedDataRunMode = sync?.progress?.savedData?.runMode;
  return savedDataRunMode || sync?.runMode || "";
}
export function catalogActivePhase(sync) {
  const requestCreationStatus = catalogPhaseStatus(
    sync,
    CATALOG_REQUEST_CREATION_PHASE,
  );
  if (catalogPhaseIsActive(requestCreationStatus)) {
    return CATALOG_REQUEST_CREATION_PHASE;
  }
  const syncStatus = catalogPhaseStatus(sync, CATALOG_SYNC_PHASE);
  if (catalogPhaseIsActive(syncStatus)) {
    return CATALOG_SYNC_PHASE;
  }
  const runtimeStatus = sync?.status || "idle";
  return runtimeStatus === "syncing" || runtimeStatus === "pausing"
    ? catalogRuntimePhase(sync)
    : "";
}
const _REVIEW_REQUIRED_MSG =
  "Curated document requires review before asset generation.";

export function requestDetails(request) {
  if (!request) {
    return "";
  }
  const checkpoint =
    request.progress?.checkpoint || request.progressCheckpoint || "";
  const savedAt = request.progress?.savedAt || request.progressSavedAt || "";
  if (checkpoint) {
    return savedAt ? `${checkpoint} (${formatDate(savedAt)})` : checkpoint;
  }
  if (request.errorMessage === _REVIEW_REQUIRED_MSG) {
    const errors = request.progress?.curatedValidation?.errors;
    if (Array.isArray(errors) && errors.length > 0) {
      return errors.join(" • ");
    }
  }
  if (request.errorMessage) {
    return request.errorMessage;
  }
  if (request.duplicateConfirmed) {
    return "Confirmed duplicate";
  }
  if (request.isConfirmedNotDuplicate) {
    return "Confirmed new";
  }
  if (request.isResumed) {
    return "Resumed from saved progress";
  }
  return "";
}
export function decodeUrlForDisplay(value) {
  const rawValue = String(value || "").trim();
  if (!rawValue) {
    return "";
  }
  try {
    return decodeURIComponent(rawValue);
  } catch {
    return rawValue;
  }
}

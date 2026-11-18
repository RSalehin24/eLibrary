import { INCOMPLETE_CATEGORY_KEYWORDS, PROCESSING_TIMEOUT_MS, iso } from "./fixtures.js";
export function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
export function categoryIsIncomplete(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return INCOMPLETE_CATEGORY_KEYWORDS.some(keyword => normalized.includes(keyword.toLowerCase()));
}
export function latestRequestForRecord(state, recordId) {
  return state.requests.filter(item => item.bookRecordId === recordId).sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))[0];
}
export function requestBlocksSelection(requestItem) {
  return requestItem && !["failed", "deleted"].includes(requestItem.state);
}
export function recordSelectable(state, recordItem) {
  const recordRequests = state.requests.filter(item => item.bookRecordId === recordItem.id);
  const confirmedDuplicate = recordRequests.find(item => item.state === "duplicate" && item.duplicateConfirmed);
  if (confirmedDuplicate) {
    const original = state.requests.find(item => item.id === confirmedDuplicate.duplicateOfRequestId);
    return !original || ["failed", "deleted"].includes(original.state);
  }
  return !recordRequests.some(requestBlocksSelection);
}
export function syncRecordStates(state) {
  state.records = state.records.map(recordItem => {
    const latest = latestRequestForRecord(state, recordItem.id);
    return {
      selectable: recordSelectable(state, recordItem),
      ...recordItem,
      bookCreationState: latest?.state || recordItem.bookCreationState,
      latestRequestId: latest?.id || null,
      selectable: recordSelectable(state, recordItem)
    };
  });
  return state;
}
export function nextRequestId(state, recordId) {
  const preferred = `request-${recordId}`;
  if (!state.requests.some(item => item.id === preferred)) {
    return preferred;
  }
  let index = 2;
  while (state.requests.some(item => item.id === `${preferred}-${index}`)) {
    index += 1;
  }
  return `${preferred}-${index}`;
}
export function createRequestForRecord(state, recordId, stateValue = "initial") {
  const timestamp = iso(30 + state.requests.length);
  state.requests.push({
    id: nextRequestId(state, recordId),
    bookRecordId: recordId,
    state: stateValue,
    createdAt: timestamp,
    updatedAt: timestamp,
    progress: null,
    errorMessage: null,
    isResumed: false,
    isConfirmedNotDuplicate: false,
    duplicateOfRequestId: null,
    duplicateOfRecordId: null,
    duplicateConfirmed: false
  });
}
export function reconcilePage(state, pageRecords) {
  for (const incoming of pageRecords) {
    const existing = state.records.find(item => item.id === incoming.id);
    if (!existing) {
      state.records.push(incoming);
      state.sync.appendedCount += 1;
      continue;
    }
    if (existing.updatedAt !== incoming.updatedAt) {
      Object.assign(existing, incoming, {
        bookCreationState: existing.bookCreationState
      });
      state.sync.updatedCount += 1;
      continue;
    }
    state.sync.skippedCount += 1;
  }
}
export function nextStateTimestamp(state) {
  return Date.parse(state.ui?.nowIso || iso(10));
}
export function applyRequestTimeouts(state) {
  const now = nextStateTimestamp(state);
  for (const item of state.requests) {
    if (item.state !== "processing") {
      continue;
    }
    const updatedAt = Date.parse(item.updatedAt || item.createdAt || "");
    if (!Number.isFinite(updatedAt) || now - updatedAt <= PROCESSING_TIMEOUT_MS) {
      continue;
    }
    item.state = "failed";
    item.errorMessage = item.errorMessage || "Processing exceeded 20 minutes without completing.";
    item.updatedAt = new Date(now).toISOString();
  }
}
export function requestDetails(item) {
  const checkpoint = item?.progress?.checkpoint || item?.progressCheckpoint || "";
  if (checkpoint) {
    return checkpoint;
  }
  if (item?.errorMessage) {
    return item.errorMessage;
  }
  if (item?.duplicateConfirmed) {
    return "Confirmed duplicate";
  }
  if (item?.isConfirmedNotDuplicate) {
    return "Confirmed new";
  }
  if (item?.isResumed) {
    return "Resumed from saved progress";
  }
  return "";
}
export function decodeUrlForDisplay(value) {
  const url = String(value || "").trim();
  if (!url) {
    return "";
  }
  try {
    return decodeURIComponent(url);
  } catch {
    return url;
  }
}
export function rowFromRecord(state, recordItem) {
  const latest = latestRequestForRecord(state, recordItem.id);
  return {
    id: recordItem.id,
    recordId: recordItem.id,
    requestId: latest?.id || null,
    title: recordItem.name,
    url: recordItem.url,
    displayUrl: recordItem.displayUrl || decodeUrlForDisplay(recordItem.url),
    displayPath: recordItem.displayPath || "",
    category: recordItem.category,
    writer: recordItem.writer,
    translator: recordItem.translator,
    publisher: recordItem.publisher,
    status: latest?.state || recordItem.bookCreationState || "not_created",
    updatedAt: latest?.updatedAt || recordItem.updatedAt,
    selectable: recordSelectable(state, recordItem),
    progressCheckpoint: latest?.progress?.checkpoint || "",
    progressSavedAt: latest?.progress?.savedAt || "",
    errorMessage: latest?.errorMessage || "",
    isResumed: Boolean(latest?.isResumed),
    isConfirmedNotDuplicate: Boolean(latest?.isConfirmedNotDuplicate),
    linkedBookId: latest?.linkedBookId || recordItem.linkedBookId || null,
    linkedBookSlug: latest?.linkedBookSlug || recordItem.linkedBookSlug || null,
    duplicateOfRequestId: latest?.duplicateOfRequestId || null,
    duplicateOfRecordId: latest?.duplicateOfRecordId || null,
    duplicateConfirmed: Boolean(latest?.duplicateConfirmed)
  };
}
export function rowFromRequest(state, requestItem) {
  const recordItem = state.records.find(item => item.id === requestItem.bookRecordId);
  if (!recordItem) {
    return null;
  }
  return {
    ...rowFromRecord(state, recordItem),
    id: requestItem.id,
    requestId: requestItem.id,
    status: requestItem.state,
    updatedAt: requestItem.updatedAt,
    selectable: true,
    progressCheckpoint: requestItem.progress?.checkpoint || "",
    progressSavedAt: requestItem.progress?.savedAt || "",
    errorMessage: requestItem.errorMessage || "",
    isResumed: Boolean(requestItem.isResumed),
    isConfirmedNotDuplicate: Boolean(requestItem.isConfirmedNotDuplicate),
    linkedBookId: requestItem.linkedBookId || recordItem.linkedBookId || null,
    linkedBookSlug: requestItem.linkedBookSlug || recordItem.linkedBookSlug || null,
    duplicateOfRequestId: requestItem.duplicateOfRequestId || null,
    duplicateOfRecordId: requestItem.duplicateOfRecordId || null,
    duplicateConfirmed: Boolean(requestItem.duplicateConfirmed)
  };
}
export function tableRowsForCard(state, card) {
  if (card === "catalog-records") {
    return [...state.records].map(recordItem => rowFromRecord(state, recordItem)).sort((left, right) => {
      const leftPriority = left.status === "not_created" ? 0 : 1;
      const rightPriority = right.status === "not_created" ? 0 : 1;
      if (leftPriority !== rightPriority) {
        return leftPriority - rightPriority;
      }
      return left.title.localeCompare(right.title);
    });
  }
  const stateMap = {
    "create-requests": ["initial"],
    "create-queue": ["queued"],
    "create-processing": ["processing"],
    "create-created": ["created"],
    "on-hold-paused": ["paused"],
    "on-hold-failed": ["failed"],
    "on-hold-duplicate": ["duplicate"],
    "on-hold-deleted": ["deleted"]
  };
  if (stateMap[card]) {
    return state.requests.filter(item => stateMap[card].includes(item.state)).map(item => rowFromRequest(state, item)).filter(Boolean);
  }
  if (card === "incomplete-records") {
    return state.records.filter(recordItem => (recordItem.wasIncomplete || categoryIsIncomplete(recordItem.category)) && !recordItem.resolvedFromIncomplete).map(recordItem => ({
      ...rowFromRecord(state, recordItem),
      selectable: false
    }));
  }
  if (card === "incomplete-completed") {
    return state.requests.filter(item => item.state === "created").map(item => rowFromRequest(state, item)).filter(item => {
      const recordItem = state.records.find(record => record.id === item.recordId);
      return recordItem?.wasIncomplete && recordItem?.resolvedFromIncomplete;
    });
  }
  return [];
}

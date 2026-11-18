import {
  INCOMPLETE_CATEGORY_KEYWORDS,
  decodeUrlForDisplay,
  requestDetails,
} from "./processingPageModel";
export function normalizeSortValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}
export function categoryIsIncomplete(value) {
  const normalizedValue = normalizeSortValue(value);
  return INCOMPLETE_CATEGORY_KEYWORDS.some((keyword) =>
    normalizedValue.includes(normalizeSortValue(keyword)),
  );
}
export function sortedUniqueValues(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((left, right) =>
    normalizeSortValue(left).localeCompare(normalizeSortValue(right)),
  );
}
export function compareRequestDates(left, right) {
  const rightUpdated = Date.parse(right?.updatedAt || "") || 0;
  const leftUpdated = Date.parse(left?.updatedAt || "") || 0;
  if (rightUpdated !== leftUpdated) {
    return rightUpdated - leftUpdated;
  }
  const rightCreated = Date.parse(right?.createdAt || "") || 0;
  const leftCreated = Date.parse(left?.createdAt || "") || 0;
  if (rightCreated !== leftCreated) {
    return rightCreated - leftCreated;
  }
  return String(left?.id || "").localeCompare(String(right?.id || ""));
}
export function latestRequestByRecordId(requests) {
  const nextMap = new Map();
  const sortedRequests = [...requests].sort(compareRequestDates);
  sortedRequests.forEach((request) => {
    if (!nextMap.has(request.bookRecordId)) {
      nextMap.set(request.bookRecordId, request);
    }
  });
  return nextMap;
}
export function requestBlocksSelection(request) {
  return request && !["failed", "deleted"].includes(request.state);
}
export function recordSelectable(record, requests, latestRequests) {
  const recordRequests = requests.filter(
    (request) => request.bookRecordId === record.id,
  );
  const confirmedDuplicate = recordRequests.find(
    (request) => request.state === "duplicate" && request.duplicateConfirmed,
  );
  if (confirmedDuplicate) {
    const original = requests.find(
      (request) => request.id === confirmedDuplicate.duplicateOfRequestId,
    );
    return !original || ["failed", "deleted"].includes(original.state);
  }
  if (recordRequests.some(requestBlocksSelection)) {
    return false;
  }
  if (typeof record.selectable === "boolean") {
    return record.selectable;
  }
  const latestRequest = latestRequests.get(record.id);
  return !requestBlocksSelection(latestRequest);
}
export function rowFromRecord(record, latestRequest, requests, latestRequests) {
  return {
    id: record.id,
    recordId: record.id,
    requestId: latestRequest?.id || record.latestRequestId || null,
    title: record.name,
    url: record.url,
    displayUrl: record.displayUrl || decodeUrlForDisplay(record.url),
    displayPath: record.displayPath || "",
    category: record.category,
    writer: record.writer,
    translator: record.translator,
    publisher: record.publisher,
    status: latestRequest?.state || record.bookCreationState || "not_created",
    updatedAt: latestRequest?.updatedAt || record.updatedAt,
    selectable: recordSelectable(record, requests, latestRequests),
    progressCheckpoint: latestRequest?.progress?.checkpoint || "",
    progressSavedAt: latestRequest?.progress?.savedAt || "",
    errorMessage: latestRequest?.errorMessage || "",
    progress: latestRequest?.progress || null,
    isResumed: Boolean(latestRequest?.isResumed),
    isConfirmedNotDuplicate: Boolean(latestRequest?.isConfirmedNotDuplicate),
    linkedBookId: latestRequest?.linkedBookId || record.linkedBookId || null,
    linkedBookSlug:
      latestRequest?.linkedBookSlug || record.linkedBookSlug || null,
    duplicateOfRequestId: latestRequest?.duplicateOfRequestId || null,
    duplicateOfRecordId:
      latestRequest?.duplicateOfRecordId || record.duplicateOfRecordId || null,
    duplicateConfirmed: Boolean(latestRequest?.duplicateConfirmed),
  };
}
export function rowFromRequest(request, record, requests, latestRequests) {
  if (!record) {
    return null;
  }
  const baseRow = rowFromRecord(record, request, requests, latestRequests);
  return {
    ...baseRow,
    id: request.id,
    requestId: request.id,
    status: request.state,
    updatedAt: request.updatedAt,
    selectable: true,
    progressCheckpoint: request.progress?.checkpoint || "",
    progressSavedAt: request.progress?.savedAt || "",
    errorMessage: request.errorMessage || "",
    progress: request.progress || null,
    isResumed: Boolean(request.isResumed),
    isConfirmedNotDuplicate: Boolean(request.isConfirmedNotDuplicate),
    linkedBookId: request.linkedBookId || record.linkedBookId || null,
    linkedBookSlug: request.linkedBookSlug || record.linkedBookSlug || null,
    duplicateOfRequestId: request.duplicateOfRequestId || null,
    duplicateOfRecordId:
      request.duplicateOfRecordId || record.duplicateOfRecordId || null,
    duplicateConfirmed: Boolean(request.duplicateConfirmed),
  };
}
export function tableRowsForCard(cardKey, records, requests) {
  const latestRequests = latestRequestByRecordId(requests);
  const recordsById = new Map(records.map((record) => [record.id, record]));
  if (cardKey === "catalog-records") {
    return [...records]
      .map((record) =>
        rowFromRecord(
          record,
          latestRequests.get(record.id),
          requests,
          latestRequests,
        ),
      )
      .sort((left, right) => {
        const leftPriority = left.status === "not_created" ? 0 : 1;
        const rightPriority = right.status === "not_created" ? 0 : 1;
        if (leftPriority !== rightPriority) {
          return leftPriority - rightPriority;
        }
        const titleComparison = normalizeSortValue(left.title).localeCompare(
          normalizeSortValue(right.title),
        );
        if (titleComparison !== 0) {
          return titleComparison;
        }
        return String(left.id || "").localeCompare(String(right.id || ""));
      });
  }
  const requestStateMap = {
    "create-requests": ["initial"],
    "create-queue": ["queued"],
    "create-processing": ["processing"],
    "create-created": ["created"],
    "on-hold-paused": ["paused"],
    "on-hold-failed": ["failed"],
    "on-hold-duplicate": ["duplicate"],
    "on-hold-deleted": ["deleted"],
  };
  if (requestStateMap[cardKey]) {
    return [...requests]
      .filter((request) => requestStateMap[cardKey].includes(request.state))
      .sort(compareRequestDates)
      .map((request) =>
        rowFromRequest(
          request,
          recordsById.get(request.bookRecordId),
          requests,
          latestRequests,
        ),
      )
      .filter(Boolean);
  }
  if (cardKey === "incomplete-records") {
    return [...records]
      .filter(
        (record) =>
          (record.wasIncomplete || categoryIsIncomplete(record.category)) &&
          !record.resolvedFromIncomplete,
      )
      .map((record) => ({
        ...rowFromRecord(
          record,
          latestRequests.get(record.id),
          requests,
          latestRequests,
        ),
        selectable: false,
      }));
  }
  if (cardKey === "incomplete-completed") {
    return [...requests]
      .filter((request) => request.state === "created")
      .sort(compareRequestDates)
      .map((request) =>
        rowFromRequest(
          request,
          recordsById.get(request.bookRecordId),
          requests,
          latestRequests,
        ),
      )
      .filter((row) => {
        const record = recordsById.get(row.recordId);
        return Boolean(record?.wasIncomplete && record?.resolvedFromIncomplete);
      });
  }
  return [];
}
export function filterTableRows(rows, filters) {
  const normalizedQuery = normalizeSortValue(filters.q);
  return rows.filter((row) => {
    const searchText = normalizeSortValue(
      [
        row.title,
        row.url,
        row.displayUrl,
        row.displayPath,
        row.writer,
        row.translator,
        row.publisher,
        row.category,
        row.status,
        requestDetails(row),
      ]
        .filter(Boolean)
        .join(" "),
    );
    if (normalizedQuery && !searchText.includes(normalizedQuery)) {
      return false;
    }
    if (filters.category && row.category !== filters.category) {
      return false;
    }
    if (filters.status && row.status !== filters.status) {
      return false;
    }
    return true;
  });
}
export function processingCardPath(cardKey) {
  const search = new URLSearchParams({
    card: cardKey,
  });
  return `/processing/card/?${search.toString()}`;
}
export function processingTablePath(
  cardKey,
  filters,
  offset,
  limit,
  includeFacets = true,
) {
  const search = new URLSearchParams({
    card: cardKey,
    offset: String(offset),
    limit: String(limit),
    includeFacets: includeFacets ? "1" : "0",
  });
  if (filters.q) {
    search.set("q", filters.q);
  }
  if (filters.category) {
    search.set("category", filters.category);
  }
  if (filters.status) {
    search.set("status", filters.status);
  }
  return `/processing/table/?${search.toString()}`;
}

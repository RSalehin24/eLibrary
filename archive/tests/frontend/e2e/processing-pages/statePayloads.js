import { categoryIsIncomplete, requestDetails, tableRowsForCard } from "./stateRows.js";
export function processingSummary(state) {
  const counts = state.requests.reduce((result, item) => {
    result[item.state] = (result[item.state] || 0) + 1;
    return result;
  }, {});
  const latestFailedMessage = state.requests.find(item => item.state === "failed" && item.errorMessage)?.errorMessage || "";
  return {
    catalog: {
      records: state.records.length,
      notCreated: state.records.filter(item => item.bookCreationState === "not_created").length,
      active: (counts.initial || 0) + (counts.queued || 0) + (counts.processing || 0),
      created: counts.created || 0,
      onHold: (counts.paused || 0) + (counts.failed || 0) + (counts.duplicate || 0) + (counts.deleted || 0)
    },
    create: {
      requests: counts.initial || 0,
      queue: counts.queued || 0,
      processing: counts.processing || 0,
      created: counts.created || 0
    },
    onHold: {
      paused: counts.paused || 0,
      failed: counts.failed || 0,
      duplicate: counts.duplicate || 0,
      deleted: counts.deleted || 0
    },
    incomplete: {
      incomplete: state.records.filter(item => (item.wasIncomplete || categoryIsIncomplete(item.category)) && !item.resolvedFromIncomplete).length,
      resolved: state.records.filter(item => item.wasIncomplete && item.resolvedFromIncomplete).length
    },
    notifications: {
      activeRequests: (counts.initial || 0) + (counts.queued || 0) + (counts.processing || 0),
      createdCount: counts.created || 0,
      failedCount: counts.failed || 0,
      duplicateCount: counts.duplicate || 0,
      latestFailedMessage
    }
  };
}
export function processingCardPayload(state, cardKey) {
  const summary = processingSummary(state);
  const cards = {
    "catalog-overview": {
      card: "catalog-overview",
      summary: summary.catalog
    },
    "catalog-sync": {
      card: "catalog-sync",
      sync: state.sync
    },
    "catalog-automation": {
      card: "catalog-automation",
      sync: state.sync,
      automation: state.automation.catalog
    },
    "create-overview": {
      card: "create-overview",
      summary: summary.create
    },
    "on-hold-overview": {
      card: "on-hold-overview",
      summary: summary.onHold
    },
    "incomplete-overview": {
      card: "incomplete-overview",
      summary: summary.incomplete
    },
    "incomplete-automation": {
      card: "incomplete-automation",
      sync: state.sync,
      automation: state.automation.incomplete
    }
  };
  return cards[cardKey] || {
    card: cardKey
  };
}
export function filteredTablePayload(state, {
  card,
  query = "",
  category = "",
  status = "",
  offset = 0,
  limit = 60,
  includeFacets = true
}) {
  const rows = tableRowsForCard(state, card);
  const normalizedQuery = String(query || "").trim().toLowerCase();
  const categoryOptions = Array.from(new Set(rows.map(row => row.category).filter(Boolean))).sort();
  const statusOptions = Array.from(new Set(rows.map(row => row.status).filter(Boolean))).sort();
  const filtered = rows.filter(row => {
    const searchText = [row.title, row.url, row.displayUrl, row.displayPath, row.writer, row.translator, row.publisher, row.category, row.status, requestDetails(row)].filter(Boolean).join(" ").toLowerCase();
    if (normalizedQuery && !searchText.includes(normalizedQuery)) {
      return false;
    }
    if (category && row.category !== category) {
      return false;
    }
    if (status && row.status !== status) {
      return false;
    }
    return true;
  });
  const nextRows = filtered.slice(offset, offset + limit);
  const nextOffset = offset + nextRows.length;
  return {
    rows: nextRows,
    pagination: {
      offset,
      limit,
      totalCount: filtered.length,
      returnedCount: nextRows.length,
      hasMore: nextOffset < filtered.length,
      nextOffset
    },
    ...(includeFacets ? {
      filters: {
        categoryOptions,
        statusOptions
      }
    } : {})
  };
}

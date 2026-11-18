import { DEFAULT_AUTOMATION_CARD, DEFAULT_SYNC_CARD } from "./processingPageModel";
export function processingCardFromState(cardKey, statePayload) {
  const sharedCard = statePayload?.cards?.[cardKey];
  if (sharedCard) {
    return sharedCard;
  }
  const summary = statePayload?.summary || {};
  const syncStates = statePayload?.syncStates || {};
  const catalogSync = syncStates.catalog || statePayload?.sync || null;
  const incompleteSync = syncStates.incomplete || statePayload?.sync || null;
  const automation = statePayload?.automation || {};
  const cards = {
    "catalog-overview": {
      card: "catalog-overview",
      summary: summary.catalog || {}
    },
    "catalog-sync": {
      card: "catalog-sync",
      sync: catalogSync || DEFAULT_SYNC_CARD
    },
    "catalog-automation": {
      card: "catalog-automation",
      sync: catalogSync || DEFAULT_SYNC_CARD,
      automation: automation.catalog || DEFAULT_AUTOMATION_CARD
    },
    "create-overview": {
      card: "create-overview",
      summary: summary.create || {}
    },
    "on-hold-overview": {
      card: "on-hold-overview",
      summary: summary.onHold || {}
    },
    "incomplete-overview": {
      card: "incomplete-overview",
      summary: summary.incomplete || {}
    },
    "incomplete-automation": {
      card: "incomplete-automation",
      sync: incompleteSync || DEFAULT_SYNC_CARD,
      automation: automation.incomplete || DEFAULT_AUTOMATION_CARD
    }
  };
  return cards[cardKey] || null;
}
export function processingCardCountFromState(cardKey, statePayload) {
  const summary = statePayload?.summary || {};
  const catalogSummary = summary.catalog || {};
  const createSummary = summary.create || {};
  const onHoldSummary = summary.onHold || {};
  const incompleteSummary = summary.incomplete || {};
  const counts = {
    "catalog-records": catalogSummary.records,
    "create-requests": createSummary.requests,
    "create-queue": createSummary.queue,
    "create-processing": createSummary.processing,
    "create-created": createSummary.created,
    "on-hold-paused": onHoldSummary.paused,
    "on-hold-failed": onHoldSummary.failed,
    "on-hold-duplicate": onHoldSummary.duplicate,
    "on-hold-deleted": onHoldSummary.deleted,
    "incomplete-records": incompleteSummary.incomplete,
    "incomplete-completed": incompleteSummary.resolved
  };
  return Number.isFinite(counts[cardKey]) ? counts[cardKey] : null;
}

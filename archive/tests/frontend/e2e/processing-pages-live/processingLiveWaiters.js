import { processingCard, processingTable } from "./processingLiveApi.js";

export async function waitForCard(page, card, predicate, options = {}) {
  const {
    attempts = 90,
    delayMs = 1000,
    description = `${card} condition`,
  } = options;
  let payload = null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    payload = await processingCard(page, card);
    if (predicate(payload)) {
      return payload;
    }
    await page.waitForTimeout(delayMs);
  }
  throw new Error(
    `Timed out waiting for ${description}. Last payload: ${JSON.stringify(payload)}`,
  );
}

export async function waitForTable(page, card, predicate, options = {}) {
  const {
    params = {},
    attempts = 90,
    delayMs = 1000,
    description = `${card} condition`,
  } = options;
  let payload = null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    payload = await processingTable(page, card, params);
    if (predicate(payload)) {
      return payload;
    }
    await page.waitForTimeout(delayMs);
  }
  throw new Error(
    `Timed out waiting for ${description}. Last payload: ${JSON.stringify(payload)}`,
  );
}

export async function waitForRequestInCards(
  page,
  cards,
  requestId,
  query,
  options = {},
) {
  const {
    attempts = 120,
    delayMs = 1000,
    description = `request ${requestId} in cards`,
  } = options;
  let snapshot = {};
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    snapshot = {};
    for (const card of cards) {
      const payload = await processingTable(page, card, { q: query });
      snapshot[card] = payload.rows.map((row) => ({
        id: row.id,
        requestId: row.requestId,
        status: row.status,
      }));
      const matchingRow = payload.rows.find(
        (row) => (row.requestId || row.id) === requestId,
      );
      if (matchingRow) {
        return { card, row: matchingRow };
      }
    }
    await page.waitForTimeout(delayMs);
  }
  throw new Error(
    `Timed out waiting for ${description}. Last snapshot: ${JSON.stringify(snapshot)}`,
  );
}

export async function waitForRecordFinalCard(page, recordId, query, options = {}) {
  const {
    attempts = 180,
    delayMs = 1000,
    description = `record ${recordId} to reach a terminal processing card`,
  } = options;
  const cards = [
    "create-requests",
    "create-queue",
    "create-processing",
    "create-created",
    "on-hold-failed",
    "on-hold-duplicate",
  ];
  let snapshot = {};
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    snapshot = {};
    for (const card of cards) {
      const payload = await processingTable(page, card, { q: query });
      snapshot[card] = payload.rows.map((row) => ({
        id: row.id,
        recordId: row.recordId,
        requestId: row.requestId,
        status: row.status,
      }));
      const matchingRow = payload.rows.find((row) => row.recordId === recordId);
      if (!matchingRow) {
        continue;
      }
      if (["create-created", "on-hold-failed", "on-hold-duplicate"].includes(card)) {
        return { card, row: matchingRow };
      }
    }
    await page.waitForTimeout(delayMs);
  }
  throw new Error(
    `Timed out waiting for ${description}. Last snapshot: ${JSON.stringify(snapshot)}`,
  );
}

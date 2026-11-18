import { getSuperAdminCredentials } from "../support/liveEnv";
import { processingPost, processingTable } from "./processingLiveApi.js";
import { waitForCard, waitForRecordFinalCard } from "./processingLiveWaiters.js";

export async function ensureCreatedRequest(
  page,
  { requireDuplicateEligible = false } = {},
) {
  const existingCreated = await processingTable(page, "create-created");
  const existingCreatedRow = existingCreated.rows.find(
    (row) => !requireDuplicateEligible || !row.isConfirmedNotDuplicate,
  );
  if (existingCreatedRow) {
    return existingCreatedRow;
  }

  const catalogTable = await processingTable(page, "catalog-records");
  const candidates = catalogTable.rows.filter((row) => row.selectable).slice(0, 5);
  if (candidates.length === 0) {
    throw new Error("No selectable catalog records are available to create a real request.");
  }

  let lastTerminalLocation = null;
  for (const candidate of candidates) {
    const response = await processingPost(
      page,
      "/processing/records/create-requests/?includeLists=0",
      { ids: [candidate.recordId || candidate.id] },
    );
    if (!response?.createdCount) {
      continue;
    }

    lastTerminalLocation = await waitForRecordFinalCard(
      page,
      candidate.recordId || candidate.id,
      candidate.title,
      {
        description: `record ${candidate.title} to finish real processing`,
      },
    );
    if (lastTerminalLocation.card === "create-created") {
      return lastTerminalLocation.row;
    }
  }

  throw new Error(
    `Unable to provision a live created request. Last terminal location: ${JSON.stringify(lastTerminalLocation)}`,
  );
}

export async function ensureDuplicateRequest(page) {
  const existingDuplicate = await processingTable(page, "on-hold-duplicate");
  if (existingDuplicate.rows.length > 0) {
    return existingDuplicate.rows[0];
  }
  throw new Error("No natural live duplicate request is currently available.");
}

export async function ensureProcessingQuiescent(page) {
  await processingPost(page, "/processing/sync/catalog/stop/?includeLists=0");
  await processingPost(page, "/processing/sync/incomplete/stop/?includeLists=0");
  await processingPost(page, "/processing/automation/catalog/?includeLists=0", {
    enabled: false,
    interval: "weekly",
    time: "03:00",
  });
  await processingPost(page, "/processing/automation/incomplete/?includeLists=0", {
    enabled: false,
    interval: "weekly",
    time: "03:00",
  });
  await waitForCard(
    page,
    "catalog-sync",
    (payload) => payload?.sync?.status === "idle",
    { description: "catalog sync to become idle" },
  );
  await waitForCard(
    page,
    "incomplete-automation",
    (payload) => payload?.sync?.status === "idle",
    { description: "incomplete sync to become idle" },
  );
  await waitForCard(
    page,
    "create-overview",
    (payload) => {
      const summary = payload?.summary || {};
      return (
        Number(summary.requests || 0) +
          Number(summary.queue || 0) +
          Number(summary.processing || 0) ===
        0
      );
    },
    { description: "processing request pipeline to become idle" },
  );
}

export async function loginSuperAdminThroughApi(page) {
  const credentials = getSuperAdminCredentials();
  await page.goto("/");
  const result = await page.evaluate(async ({ email, password }) => {
    await fetch("/api/csrf/", { credentials: "include" });
    const csrfMatch = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    const response = await fetch("/api/auth/login/", {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(csrfMatch
          ? { "X-CSRFToken": decodeURIComponent(csrfMatch[1]) }
          : {}),
      },
      body: JSON.stringify({ email, password }),
    });
    const text = await response.text();
    return {
      ok: response.ok,
      status: response.status,
      text,
    };
  }, credentials);

  if (!result.ok) {
    throw new Error(`API login failed with ${result.status}: ${result.text}`);
  }
}

export function nextMinuteTimeString() {
  const nextMinute = new Date();
  nextMinute.setMinutes(nextMinute.getMinutes() + 1, 0, 0);
  const hours = String(nextMinute.getHours()).padStart(2, "0");
  const minutes = String(nextMinute.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

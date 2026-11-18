import { expect, test } from "./support/playwright";
import { processingPost, processingTable } from "./processing-pages-live/processingLiveApi.js";
import { waitForCard } from "./processing-pages-live/processingLiveWaiters.js";
import { ensureProcessingQuiescent, loginSuperAdminThroughApi, nextMinuteTimeString } from "./processing-pages-live/processingLiveSetup.js";

test.describe("processing live incomplete runtime coverage", () => {
  test.beforeEach(async ({ page }) => {
    await loginSuperAdminThroughApi(page);
    await ensureProcessingQuiescent(page);
  });

  test("incomplete automation stays separate from catalog runtime and incomplete counts are server-backed", async ({
    page,
  }) => {
    test.setTimeout(120_000);

    await page.goto("/incomplete", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("incomplete-page")).toBeVisible({
      timeout: 30_000,
    });

    const incompleteTable = await processingTable(page, "incomplete-records");
    await expect.poll(
      async () =>
        (await page.getByTestId("incomplete-records-count").textContent())?.trim(),
    ).toBe(String(incompleteTable.pagination.totalCount));

    await page.getByTestId("incomplete-automation-run-btn").click();
    await waitForCard(
      page,
      "incomplete-automation",
      (payload) => ["syncing", "pausing", "paused"].includes(payload?.sync?.status),
      { description: "incomplete automation to start" },
    );

    await page.goto("/catalog");
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeEnabled();

    await processingPost(page, "/processing/sync/incomplete/stop/?includeLists=0");
  });

  test("scheduled incomplete automation uses the same live runtime as the run button", async ({
    page,
  }) => {
    test.setTimeout(180_000);

    const scheduledTime = nextMinuteTimeString();
    await page.goto("/incomplete", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("incomplete-page")).toBeVisible({
      timeout: 30_000,
    });

    const toggle = page.getByTestId("incomplete-automation-enabled");
    if (!(await toggle.isChecked())) {
      await toggle.check();
    }
    await page
      .getByTestId("incomplete-automation-interval")
      .selectOption("daily");
    await page.getByTestId("incomplete-automation-time").fill(scheduledTime);
    await page.getByTestId("incomplete-automation-save-btn").click();

    await expect(page.getByTestId("incomplete-automation-status")).toContainText(
      "Saved",
    );

    const scheduledRun = await waitForCard(
      page,
      "incomplete-automation",
      (payload) =>
        payload?.sync?.triggerSource === "scheduler" &&
        payload?.sync?.runMode === "incomplete_automation" &&
        ["syncing", "pausing", "paused"].includes(payload?.sync?.status),
      {
        attempts: 150,
        delayMs: 1000,
        description: "scheduled incomplete automation to start",
      },
    );

    expect(scheduledRun.sync.triggerSource).toBe("scheduler");
    await page.goto("/catalog", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeEnabled();

    await processingPost(page, "/processing/sync/incomplete/stop/?includeLists=0");
    await processingPost(page, "/processing/automation/incomplete/?includeLists=0", {
      enabled: false,
      interval: "weekly",
      time: "03:00",
    });
  });
});

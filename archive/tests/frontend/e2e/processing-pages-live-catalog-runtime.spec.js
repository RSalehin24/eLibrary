import { expect, test } from "./support/playwright";
import { processingPost, processingTable } from "./processing-pages-live/processingLiveApi.js";
import { waitForCard } from "./processing-pages-live/processingLiveWaiters.js";
import { ensureProcessingQuiescent, loginSuperAdminThroughApi, nextMinuteTimeString } from "./processing-pages-live/processingLiveSetup.js";

test.describe("processing live catalog runtime coverage", () => {
  test.beforeEach(async ({ page }) => {
    await loginSuperAdminThroughApi(page);
    await ensureProcessingQuiescent(page);
  });

  test("catalog manual runtime disables automation and catalog count stays server-backed", async ({
    page,
  }) => {
    test.setTimeout(120_000);

    await page.goto("/catalog", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("catalog-page")).toBeVisible({
      timeout: 30_000,
    });

    const initialTable = await processingTable(page, "catalog-records");
    await expect.poll(
      async () =>
        (await page.getByTestId("catalog-records-count").textContent())?.trim(),
    ).toBe(String(initialTable.pagination.totalCount));

    if (initialTable.rows.length > 0) {
      const query = initialTable.rows[0].title;
      await page.getByTestId("catalog-records-search").fill(query);
      const filtered = await processingTable(page, "catalog-records", { q: query });
      await expect.poll(
        async () =>
          (await page.getByTestId("catalog-records-count").textContent())?.trim(),
      ).toBe(String(filtered.pagination.totalCount));
    }

    await page.getByTestId("catalog-sync-start-btn").click();
    await expect(page.getByTestId("catalog-sync-pause-btn")).toBeVisible();
    await expect(page.getByTestId("catalog-automation-run-btn")).toBeDisabled();

    await page.getByTestId("catalog-sync-pause-btn").click();
    await waitForCard(
      page,
      "catalog-sync",
      (payload) => payload?.sync?.status === "paused",
      { description: "manual catalog pause" },
    );

    await expect(page.getByTestId("catalog-sync-resume-btn")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("catalog-automation-run-btn")).toHaveAttribute(
      "aria-label",
      "Resume automated catalog sync",
    );

    await processingPost(page, "/processing/sync/catalog/stop/?includeLists=0");
  });

  test("catalog automation run button shares the same runtime ownership as manual", async ({
    page,
  }) => {
    test.setTimeout(120_000);

    await page.goto("/catalog");
    await page.getByTestId("catalog-automation-run-btn").click();

    await expect.poll(
      async () => (await page.getByTestId("catalog-automation-run-btn").getAttribute("data-state")) || "",
    ).toMatch(/syncing|pausing|paused/);
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeDisabled({
      timeout: 30_000,
    });

    await page.getByTestId("catalog-automation-run-btn").click();
    await waitForCard(
      page,
      "catalog-automation",
      (payload) => payload?.sync?.status === "paused",
      { description: "catalog automation pause" },
    );

    await expect(page.getByTestId("catalog-sync-resume-btn")).toBeVisible();
    await processingPost(page, "/processing/sync/catalog/stop/?includeLists=0");
  });

  test("scheduled catalog automation uses the same live runtime as button-started automation", async ({
    page,
  }) => {
    test.setTimeout(180_000);

    const scheduledTime = nextMinuteTimeString();
    await page.goto("/catalog");

    const toggle = page.getByTestId("catalog-automation-enabled");
    if (!(await toggle.isChecked())) {
      await toggle.check();
    }
    await page.getByTestId("catalog-automation-interval").selectOption("daily");
    await page.getByTestId("catalog-automation-time").fill(scheduledTime);
    await page.getByTestId("catalog-automation-save-btn").click();

    await expect(page.getByTestId("catalog-automation-status")).toContainText("Saved");

    const scheduledRun = await waitForCard(
      page,
      "catalog-automation",
      (payload) =>
        payload?.sync?.triggerSource === "scheduler" &&
        payload?.sync?.runMode === "catalog_automation" &&
        ["syncing", "pausing", "paused"].includes(payload?.sync?.status),
      {
        attempts: 150,
        delayMs: 1000,
        description: "scheduled catalog automation to start",
      },
    );

    expect(scheduledRun.sync.triggerSource).toBe("scheduler");
    await expect(page.getByTestId("catalog-sync-start-btn")).toBeDisabled();

    await processingPost(page, "/processing/sync/catalog/stop/?includeLists=0");
    await processingPost(page, "/processing/automation/catalog/?includeLists=0", {
      enabled: false,
      interval: "weekly",
      time: "03:00",
    });
  });
});

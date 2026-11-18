import { expect, test } from "./support/playwright";
import { processingTable } from "./processing-pages-live/processingLiveApi.js";
import { waitForRequestInCards, waitForTable } from "./processing-pages-live/processingLiveWaiters.js";
import { ensureDuplicateRequest, ensureProcessingQuiescent, loginSuperAdminThroughApi } from "./processing-pages-live/processingLiveSetup.js";

test.describe("processing live duplicate resolution coverage", () => {
  test.beforeEach(async ({ page }) => {
    await loginSuperAdminThroughApi(page);
    await ensureProcessingQuiescent(page);
  });

  test("duplicate resolution keeps counts server-backed and moves the request out of duplicate", async ({
    page,
  }) => {
    test.setTimeout(180_000);

    await page.goto("/on-hold", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("on-hold-page")).toBeVisible({
      timeout: 30_000,
    });

    let duplicateRow = null;
    try {
      duplicateRow = await ensureDuplicateRequest(page);
    } catch (error) {
      test.skip(
        true,
        error instanceof Error ? error.message : "No live duplicate request is available.",
      );
    }
    const duplicateRequestId = duplicateRow.requestId || duplicateRow.id;
    const duplicateTable = await processingTable(page, "on-hold-duplicate");

    await expect.poll(
      async () =>
        (await page.getByTestId("on-hold-duplicate-count").textContent())?.trim(),
    ).toBe(String(duplicateTable.pagination.totalCount));

    await page.getByTestId("on-hold-duplicate-search").fill(duplicateRow.title);
    const filteredDuplicateTable = await processingTable(page, "on-hold-duplicate", {
      q: duplicateRow.title,
    });
    await expect.poll(
      async () =>
        (await page.getByTestId("on-hold-duplicate-count").textContent())?.trim(),
    ).toBe(String(filteredDuplicateTable.pagination.totalCount));

    await expect(
      page.getByTestId(`on-hold-duplicate-select-${duplicateRequestId}`),
    ).toBeVisible({
      timeout: 30_000,
    });
    await page.getByTestId(`on-hold-duplicate-select-${duplicateRequestId}`).check();
    await page.getByTestId("on-hold-duplicate-new-btn").click();

    await waitForTable(
      page,
      "on-hold-duplicate",
      (payload) =>
        !payload.rows.some(
          (row) => (row.requestId || row.id) === duplicateRequestId,
        ),
      {
        params: { q: duplicateRow.title },
        description: "duplicate request to leave duplicate card after marking new",
      },
    );

    const relocated = await waitForRequestInCards(
      page,
      [
        "create-requests",
        "create-queue",
        "create-processing",
        "create-created",
        "on-hold-failed",
      ],
      duplicateRequestId,
      duplicateRow.title,
      {
        attempts: 180,
        description: "resolved duplicate request to re-enter live processing flow",
      },
    );

    expect(
      [
        "create-requests",
        "create-queue",
        "create-processing",
        "create-created",
        "on-hold-failed",
      ],
    ).toContain(relocated.card);
  });
});

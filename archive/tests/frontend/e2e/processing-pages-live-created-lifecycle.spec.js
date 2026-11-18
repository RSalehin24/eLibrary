import { expect, test } from "./support/playwright";
import { processingTable } from "./processing-pages-live/processingLiveApi.js";
import { waitForRequestInCards, waitForTable } from "./processing-pages-live/processingLiveWaiters.js";
import { ensureCreatedRequest, ensureProcessingQuiescent, loginSuperAdminThroughApi } from "./processing-pages-live/processingLiveSetup.js";

test.describe("processing live created lifecycle coverage", () => {
  test.beforeEach(async ({ page }) => {
    await loginSuperAdminThroughApi(page);
    await ensureProcessingQuiescent(page);
  });

  test("created deletion hydrates deleted card and create again returns the request to live flow", async ({
    page,
  }) => {
    test.setTimeout(180_000);

    await page.goto("/create", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("create-page")).toBeVisible({
      timeout: 30_000,
    });

    const createdRow = await ensureCreatedRequest(page);
    const createdRequestId = createdRow.requestId || createdRow.id;
    const createdTable = await processingTable(page, "create-created");

    await expect.poll(
      async () =>
        (await page.getByTestId("create-created-count").textContent())?.trim(),
    ).toBe(String(createdTable.pagination.totalCount));

    await page.getByTestId("create-created-search").fill(createdRow.title);
    const filteredCreatedTable = await processingTable(page, "create-created", {
      q: createdRow.title,
    });
    await expect.poll(
      async () =>
        (await page.getByTestId("create-created-count").textContent())?.trim(),
    ).toBe(String(filteredCreatedTable.pagination.totalCount));

    await expect(
      page.getByTestId(`create-created-select-${createdRequestId}`),
    ).toBeVisible({
      timeout: 30_000,
    });
    await page.getByTestId(`create-created-select-${createdRequestId}`).check();
    await page.getByTestId("create-created-delete-btn").click();

    await waitForTable(
      page,
      "on-hold-deleted",
      (payload) =>
        payload.rows.some(
          (row) => (row.requestId || row.id) === createdRequestId,
        ),
      {
        params: { q: createdRow.title },
        description: "deleted card to hydrate after deleting a created request",
      },
    );

    await page.goto("/on-hold", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("on-hold-page")).toBeVisible({
      timeout: 30_000,
    });

    await page.getByTestId("on-hold-deleted-search").fill(createdRow.title);
    const deletedFilteredTable = await processingTable(page, "on-hold-deleted", {
      q: createdRow.title,
    });
    await expect.poll(
      async () =>
        (await page.getByTestId("on-hold-deleted-count").textContent())?.trim(),
    ).toBe(String(deletedFilteredTable.pagination.totalCount));

    await expect(
      page.getByTestId(`on-hold-deleted-select-${createdRequestId}`),
    ).toBeVisible({
      timeout: 30_000,
    });
    await page.getByTestId(`on-hold-deleted-select-${createdRequestId}`).check();
    await page.getByTestId("on-hold-deleted-create-again-btn").click();

    const emptyDeletedTable = await waitForTable(
      page,
      "on-hold-deleted",
      (payload) =>
        payload.pagination.totalCount === 0 &&
        !payload.rows.some((row) => (row.requestId || row.id) === createdRequestId),
      {
        params: { q: createdRow.title },
        description: "recreated request to leave the deleted card",
      },
    );
    expect(emptyDeletedTable.pagination.totalCount).toBe(0);

    const relocated = await waitForRequestInCards(
      page,
      [
        "create-created",
        "on-hold-failed",
      ],
      createdRequestId,
      createdRow.title,
      {
        attempts: 180,
        description: "recreated request to finish processing again",
      },
    );

    expect(["create-created", "on-hold-failed"]).toContain(relocated.card);
  });
});

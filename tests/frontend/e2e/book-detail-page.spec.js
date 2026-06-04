import { expect, test } from "./support/playwright";
import { BookDetailPageModel } from "./pages/bookDetailPage";
import {
  installWindowOpenRecorder,
  loginAsSuperAdmin,
  readOpenedUrls,
} from "./support/liveApp";
import { seedData } from "./support/seedData";

async function openReaderFromBookDetail(page, slug = seedData.books.detail.slug) {
  const bookPage = new BookDetailPageModel(page);

  await bookPage.goto(slug);
  await bookPage.openReaderButton().click();

  await expect(page).toHaveURL(/\/reader\?/);
  await expect
    .poll(() => new URL(page.url()).searchParams.get("manifest"), {
      timeout: 15_000,
    })
    .toBeTruthy();
  await expect(page.locator("#reader-view")).toBeVisible();
  await expect(page.locator("#viewer iframe")).toBeVisible({
    timeout: 15_000,
  });

  return bookPage;
}

test.describe("Book Detail Page", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page);
  });

  test("book detail shows the fetched table of contents summary", async ({
    page,
  }) => {
    const bookPage = new BookDetailPageModel(page);

    await bookPage.goto(seedData.books.detail.slug);

    await expect(
      page.getByRole("heading", { name: "Table of Contents", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Entities and Details", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Chapter 1", { exact: true }).first()).toBeVisible();
  });

  test("open reader launches the reader route from the book detail page", async ({
    page,
  }) => {
    const bookPage = new BookDetailPageModel(page);

    await bookPage.goto(seedData.books.detail.slug);
    await expect(bookPage.sendToKindleButton()).toBeVisible();
    await bookPage.openReaderButton().click();

    await expect(page).toHaveURL(/\/reader\?/);
    await expect
      .poll(() => new URL(page.url()).searchParams.get("manifest"), {
        timeout: 15_000,
      })
      .toBeTruthy();
    await expect(page.locator("#reader-view")).toBeVisible();
  });

  test("reader controls stay functional after the epub loads", async ({
    page,
  }) => {
    await openReaderFromBookDetail(page);

    const readerFrameBody = page.frameLocator("#viewer iframe").locator("body");
    const tocToggle = page.getByRole("button", {
      name: "Toggle table of contents",
    });
    const settingsButton = page.getByRole("button", {
      name: "Open reading settings",
    });
    const settingsPanel = page.locator("#reader-settings-panel");
    const tocItems = page.locator(".slide-contents-item-label");

    await expect(readerFrameBody).toContainText(/\S+/, { timeout: 15_000 });

    await expect(tocToggle).toHaveAttribute("aria-expanded", "true");
    await tocToggle.click();
    await expect(tocToggle).toHaveAttribute("aria-expanded", "false");
    await tocToggle.click();
    await expect(tocToggle).toHaveAttribute("aria-expanded", "true");
    await expect(tocItems.first()).toBeVisible();

    const tocItemCount = await tocItems.count();
    const tocTarget = tocItems.nth(tocItemCount > 1 ? 1 : 0);
    await tocTarget.click();
    await expect(tocTarget).toHaveAttribute("aria-current", "true");

    await settingsButton.click();
    await expect(settingsPanel).toHaveAttribute("aria-hidden", "false");

    const initialFontSize = await page.evaluate(
      () => Number(window.localStorage.getItem("epub_reader_font_size") || "20"),
    );
    await page.getByRole("button", { name: "Increase font size" }).click();
    await expect
      .poll(() =>
        page.evaluate(() =>
          Number(window.localStorage.getItem("epub_reader_font_size") || "0"),
        ),
      )
      .toBeGreaterThan(initialFontSize);

    const nightThemeButton = page.getByRole("button", { name: "Night" });
    await nightThemeButton.click();
    await expect(nightThemeButton).toHaveAttribute("aria-pressed", "true");
    await expect
      .poll(() =>
        page.evaluate(() => window.localStorage.getItem("epub_reader_theme_index")),
      )
      .toBe("2");

    await page.getByRole("button", { name: "Next section" }).click();
    await expect(page.locator("#viewer iframe")).toBeVisible();
  });

  test("removing a bookmark does not clear metadata edits in progress", async ({
    page,
  }) => {
    const bookPage = new BookDetailPageModel(page);
    const updatedTitle = "E2E Detail Book Updated";

    await bookPage.goto(seedData.books.detail.slug);
    try {
      await bookPage.fillMetadataTitle(updatedTitle);
      await bookPage.removeBookmark(seedData.bookmark.label);
      await bookPage.saveMetadata();

      await expect(page).toHaveURL(/\/books\/e2e-detail-book-updated$/);
      await page.reload();
      await expect(bookPage.titleInput()).toHaveValue(updatedTitle);
      await expect(page.getByText(seedData.bookmark.label)).toHaveCount(0);
      await expect(page.getByText("Opening")).toHaveCount(0);
    } finally {
      await bookPage.fillMetadataTitle(seedData.books.detail.title);
      await bookPage.saveMetadata();
      await expect(page).toHaveURL(new RegExp(`/books/${seedData.books.detail.slug}$`));
    }
  });

  test("preview locks only disable html preview while other book actions keep working", async ({
    page,
  }) => {
    await installWindowOpenRecorder(page);
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "ebook_preview_lock:/api/access/books/e2e-preview-book/download/html/",
        JSON.stringify({ tabId: "tab-1", ts: Date.now() }),
      );
    });
    const bookPage = new BookDetailPageModel(page);

    await bookPage.goto(seedData.books.preview.slug);
    await expect(bookPage.htmlPreviewButton()).toBeDisabled();
    await expect(bookPage.epubButton()).toBeEnabled();

    const expectedEpubUrl = new URL(
      `/api/access/books/${seedData.books.preview.slug}/download/epub/`,
      page.url(),
    ).toString();

    await bookPage.epubButton().click();
    await expect
      .poll(async () => readOpenedUrls(page))
      .toContain(expectedEpubUrl);
  });
});

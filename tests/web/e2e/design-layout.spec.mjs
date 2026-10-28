import { writeFileSync } from "node:fs";
import { test, expect, useAccount } from "./fixtures.mjs";
import { layoutRoutes } from "./layout-routes.mjs";

let inventory;
test.beforeAll(async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL });
  try { inventory = await layoutRoutes(await context.newPage()); }
  finally { await context.close(); }
});

function layoutBreaks() {
  const problems = [];
  if (document.documentElement.scrollWidth > innerWidth) problems.push({ element: "document", width: document.documentElement.scrollWidth, viewport: innerWidth });
  const readerNavigation = document.querySelector('.site-header[data-workspace="reader"]>.primary-navigation');
  if (readerNavigation?.checkVisibility() && getComputedStyle(readerNavigation).position === "fixed" && parseFloat(getComputedStyle(document.body).paddingBottom) + 1 < readerNavigation.getBoundingClientRect().height) problems.push({ element: "reader-navigation", issue: "Bottom navigation covers the end of the page" });
  const sidebar = document.querySelector(".admin-sidebar"), navigation = (sidebar?.querySelector(".admin-navigation-drawer[open] nav") ?? sidebar?.querySelector(".admin-desktop-navigation nav"));
  const menuTrigger = sidebar?.querySelector(".admin-menu-trigger");
  if (innerWidth < 900 && menuTrigger && sidebar.getBoundingClientRect().height > menuTrigger.getBoundingClientRect().height + 24) problems.push({ element: "admin-sidebar", issue: "Navigation row stretched above the content" });
  const current = navigation?.querySelector('[aria-current="page"]');
  if (innerWidth < 900 && current?.checkVisibility() && (current.getBoundingClientRect().left < navigation.getBoundingClientRect().left - 1 || current.getBoundingClientRect().right > navigation.getBoundingClientRect().right + 1)) problems.push({ element: "admin-sidebar", issue: "Active section outside navigation viewport" });
  const results = document.querySelector(".book-grid, .managed-books-table"), exports = document.querySelector(".catalog-export-controls");
  if (results && exports && !(results.compareDocumentPosition(exports) & Node.DOCUMENT_POSITION_FOLLOWING)) problems.push({ element: "book-results", issue: "Downloads placed before books" });
  if (innerWidth >= 1100 && parseFloat(getComputedStyle(document.documentElement).fontSize) <= 16 && document.querySelector(".catalog-controls") && results?.querySelector(".book-card") && results.getBoundingClientRect().top >= innerHeight) problems.push({ element: "book-results", issue: "Primary results pushed below the desktop viewport" });
  for (const node of document.querySelectorAll("main h1, main h2, main .button, main fieldset, main legend")) {
    const box = node.getBoundingClientRect();
    if (!box.width || !box.height || !node.checkVisibility() || box.width <= 2) continue;
    if (node.scrollWidth > node.clientWidth + 2) problems.push({ element: node.tagName, class: node.className, text: node.textContent.slice(0, 60), width: node.clientWidth, content: node.scrollWidth });
  }
  for (const control of document.querySelectorAll("main select")) if (control.checkVisibility() && control.getBoundingClientRect().height < 43) problems.push({ element: "SELECT", issue: "Dropdown is smaller than the minimum touch target" });
  return problems;
}

async function inspectLayout(page, message) {
  let problems;
  // ResizeObserver aligns the active section after the browser applies a resize.
  await expect.configure({ soft: true }).poll(async () => {
    problems = await page.evaluate(layoutBreaks);
    return problems;
  }, { message }).toEqual([]);
  const trigger = page.locator(".admin-menu-trigger");
  if (await trigger.isVisible()) {
    await trigger.click();
    const drawerProblems = await page.evaluate(layoutBreaks);
    problems.push(...drawerProblems);
    await page.keyboard.press("Escape");
    await expect(page.locator(".admin-navigation-drawer")).not.toBeVisible();
  }
  expect.soft(problems, message).toEqual([]);
  return problems;
}

for (const name of ["public", "authentication", "personal", "kindle", "admin-catalog", "admin-processing", "admin-access", "missing-pages"]) {
  test(`${name} layouts fit phones, tablets, desktop and enlarged text in both languages`, async ({ page, baseURL }, info) => {
    test.setTimeout(180_000);
    const group = inventory.find(entry => entry.name === name), results = [];
    // Audit fresh server responses; WebKit otherwise revalidates the offline entry with 304.
    await page.route("**/*", route => route.continue());
    if (group.account) await useAccount(page, group.account);
    for (const language of ["bn", "en"]) {
      await page.context().addCookies([{ name: "library-language", value: language, url: baseURL }]);
      for (const [key, pathname] of group.routes) {
        const response = await page.goto(pathname);
        expect.soft(response.status(), `${key}: HTTP response`).toBe(group.status ?? 200);
        await page.locator("main").waitFor(); await page.evaluate(() => document.fonts.ready);
        await expect.soft(page.locator("html"), `${key}: persistent language`).toHaveAttribute("lang", language);
        for (const width of [320, 390, 820, 1366, 1920]) {
          await page.setViewportSize({ width, height: 900 });
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
          const problems = await inspectLayout(page, `${key}: ${language}, ${width}px`);
          results.push({ key, language, width, scale: 1, problems });
          if (language === "bn" && width !== 820) await page.screenshot({ path: info.outputPath(`${key}-${language}-${width}.png`), fullPage: true });
        }
        for (const width of [320, 390, 820, 1366, 1920]) {
          await page.setViewportSize({ width, height: 900 });
          const style = await page.addStyleTag({ content: "html { font-size:200%; }" });
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          const problems = await inspectLayout(page, `${key}: ${language}, ${width}px, 200% text`);
          results.push({ key, language, width, scale: 2, problems });
          await style.evaluate(node => node.remove());
        }
      }
    }
    writeFileSync(info.outputPath("layout-review.json"), JSON.stringify(results, null, 2));
  });
}

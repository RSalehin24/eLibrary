import { expect } from "../support/playwright";

export class ProcessingPageModel {
  constructor(page) {
    this.page = page;
  }

  async goto(path, heading) {
    await this.page.goto(path);
    await expect(
      this.page.getByRole("heading", {
        name: heading,
        exact: true,
        level: 1,
      }),
    ).toBeVisible({ timeout: 15_000 });
  }

  pageHeader(heading) {
    return this.page.locator("section.detail-card", {
      has: this.page.getByRole("heading", {
        name: heading,
        exact: true,
        level: 1,
      }),
    });
  }

  headerSpinner(heading) {
    return this.pageHeader(heading).locator(".panel-header .loading-spinner");
  }

  card(title) {
    return this.page.locator("section.processing-card", {
      has: this.page.getByRole("heading", { name: title, exact: true }),
    });
  }

  catalogSyncButton() {
    return this.card("Catalog Books").locator(".catalog-toolbar-sync-button");
  }

  catalogSyncStatus() {
    return this.card("Catalog Books").locator(".catalog-toolbar-sync-status");
  }

  catalogCreateSelectedButton() {
    return this.card("Catalog Books")
      .locator(".processing-card-actions .primary-button")
      .first();
  }

  catalogRowCheckbox(title) {
    return this.card("Catalog Books").getByLabel(`Select ${title}`);
  }

  cardHead(title) {
    return this.card(title).locator(".processing-card-head");
  }

  cardCountPill(title) {
    return this.card(title).locator(".processing-card-count");
  }

  cardSearchInput(title) {
    return this.card(title).locator('input[type="search"]').first();
  }

  cardResultCount(title) {
    return this.card(title).locator(".catalog-result-count").first();
  }

  cardFilterButton(title) {
    return this.card(title)
      .getByRole("button", { name: /^Filters/ })
      .first();
  }

  cardFilterDrawer(title) {
    return this.card(title).locator(".catalog-filter-drawer").first();
  }

  cardOpenFilterDrawer(title) {
    return this.card(title).locator(".catalog-filter-drawer.is-open").first();
  }

  tableRows(title) {
    return this.card(title).locator("tbody tr");
  }

  collapsibleStack() {
    return this.page.locator(".processing-collapsible-stack");
  }

  rowInCard(title, pattern) {
    return this.card(title)
      .getByRole("row")
      .filter({ hasText: pattern })
      .first();
  }

  rowActionButton(title, rowPattern, buttonName) {
    return this.rowInCard(title, rowPattern).getByRole("button", {
      name: buttonName,
    });
  }

  async searchCard(title, query) {
    const card = this.card(title);
    const input = card.locator('input[type="search"]').first();
    await expect(input).toBeVisible();
    await input.fill(query);
    await input.evaluate((node) => node.form?.requestSubmit());
    return card;
  }

  async openCardFilters(title) {
    const button = this.cardFilterButton(title);
    await expect(button).toBeVisible();
    await button.click();
    return this.card(title);
  }

  async toggleCard(title) {
    const card = this.card(title);
    const button = card.getByRole("button", { name: /Expand|Collapse/ }).first();
    await expect(button).toBeVisible();
    await button.click();
    return card;
  }

  async expandCard(title) {
    const card = this.card(title);
    await expect(card).toBeVisible();
    const expandButton = card.getByRole("button", { name: "Expand" }).first();
    if (await expandButton.count()) {
      const isVisible = await expandButton.isVisible().catch(() => false);
      if (!isVisible) {
        return card;
      }
      await expandButton.click();
    }
    return card;
  }

  async saveAutomation({
    title = "Automation",
    enabled,
    time,
    frequency,
    mode,
    pages,
  }) {
    const card = this.card(title);
    const toggle = card.locator('.processing-switch input[type="checkbox"]');
    const toggleLabel = card.locator(".processing-switch");

    if (enabled !== undefined) {
      let isChecked = await toggle.isChecked();
      for (let attempt = 0; attempt < 3 && isChecked !== enabled; attempt += 1) {
        await toggleLabel.click();
        await this.page.waitForTimeout(150);
        isChecked = await toggle.isChecked();
      }
      if (isChecked !== enabled) {
        throw new Error(`Unable to set automation toggle to ${enabled}.`);
      }
    }

    if (time) {
      await card.locator('input[type="time"]').fill(time);
    }

    const selects = card.locator("select");
    if (frequency) {
      await selects.first().selectOption(frequency);
    }
    if (mode && (await selects.count()) > 1) {
      await selects.nth(1).selectOption(mode);
    }

    if (pages !== undefined) {
      await card.locator('input[type="number"]').fill(String(pages));
    }

    await card.getByRole("button", { name: "Save automation" }).click();
    await expect(this.page.getByText("Automation saved.")).toBeVisible();
  }

  async selectIncompleteBook(title) {
    await this.card("Incomplete")
      .getByLabel(`Select ${title}`)
      .check();
  }

  async reprocessSelectedIncomplete() {
    await this.card("Incomplete")
      .getByRole("button", { name: "Reprocess selected" })
      .click();
  }

  async confirmDialog(confirmLabel = "Delete") {
    const dialog = this.page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: confirmLabel }).click();
  }
}

import { expect } from "../support/playwright";

export class ManualBooksPageModel {
  constructor(page) {
    this.page = page;
  }

  async goto() {
    await this.page.goto("/manual-books");
    await expect(
      this.page.getByRole("heading", { name: "Physical Books' List" }),
    ).toBeVisible();
  }

  async openComposer() {
    await this.page.getByRole("button", { name: "Add manual book" }).click();
    await expect(this.page.locator("#manual-book-composer")).toBeVisible();
  }

  async fillTitle(value) {
    await this.page.locator("#manual-book-composer").getByLabel("Title").fill(value);
  }

  async addTag(label, value) {
    const input = this.page
      .locator("#manual-book-composer")
      .locator("label.tag-field", {
        has: this.page.getByText(label, { exact: true }),
      })
      .locator("input");
    await input.fill(value);
    await input.press("Enter");
  }

  async fillTagWithoutEnter(label, value) {
    const input = this.page
      .locator("#manual-book-composer")
      .locator("label.tag-field", {
        has: this.page.getByText(label, { exact: true }),
      })
      .locator("input");
    await input.fill(value);
  }

  async clickDone() {
    await this.page
      .locator("#manual-book-composer")
      .getByRole("button", { name: "Done", exact: true })
      .click();
  }

  async clickClear() {
    await this.page
      .locator("#manual-book-composer")
      .getByRole("button", { name: "Clear fields" })
      .click();
  }

  async closeComposerWithToolbar() {
    await this.page.getByRole("button", { name: "Close add book form" }).click();
  }

  async expectComposerVisible(visible = true) {
    if (visible) {
      await expect(this.page.locator("#manual-book-composer")).toBeVisible();
    } else {
      await expect(this.page.locator("#manual-book-composer")).toBeHidden();
    }
  }

  async submit() {
    await this.page
      .locator("#manual-book-composer")
      .getByRole("button", { name: "Add & next" })
      .click();
  }

  async search(query) {
    const search = this.page.getByPlaceholder(
      "Search manual books, book IDs, writers...",
    );
    await search.fill(query);
    await search.press("Enter");
  }
}

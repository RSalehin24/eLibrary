import { expect } from "../support/playwright";

export class CatalogPropertyPageModel {
  constructor(page, { path, heading, searchPlaceholder }) {
    this.page = page;
    this.path = path;
    this.heading = heading;
    this.searchInput = page.getByPlaceholder(searchPlaceholder);
  }

  async goto() {
    await this.page.goto(this.path);
    await expect(
      this.page.getByRole("heading", { name: this.heading, exact: true }),
    ).toBeVisible();
  }

  async search(query) {
    await this.searchInput.fill(query);
    await this.searchInput.press("Enter");
  }

  async openResult(label) {
    const row = this.page.locator("tbody tr").filter({
      has: this.page.getByText(label, { exact: true }),
    });
    await row.getByRole("link", { name: "Open" }).click();
  }
}

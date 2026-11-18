import { expect } from "../support/playwright";

export class BookDetailPageModel {
  constructor(page) {
    this.page = page;
    this.hero = page.getByTestId("book-detail-hero");
    this.metadataWorkspace = page.getByTestId("book-metadata-workspace");
  }

  async goto(slug = "mock-book") {
    await this.page.goto(`/books/${slug}`);
    await expect(this.hero).toBeVisible();
  }

  titleInput() {
    return this.metadataWorkspace.getByLabel("Title");
  }

  summaryInput() {
    return this.metadataWorkspace.getByLabel("Summary");
  }

  async fillMetadataTitle(value) {
    await this.titleInput().fill(value);
  }

  async fillMetadataSummary(value) {
    await this.summaryInput().fill(value);
  }

  async saveMetadata() {
    await this.metadataWorkspace
      .getByRole("button", { name: "Save metadata" })
      .click();
  }

  async saveReview() {
    await this.metadataWorkspace
      .getByRole("button", { name: "Save review" })
      .click();
  }

  async setReviewState(value) {
    await this.metadataWorkspace.getByLabel("Review state").selectOption(value);
  }

  async setReviewNotes(value) {
    await this.metadataWorkspace.getByLabel("Notes").fill(value);
  }

  async approveReview() {
    await this.metadataWorkspace
      .getByRole("button", { name: "Approve" })
      .first()
      .click();
  }

  async removeBookmark(label) {
    const card = this.page.locator(".notes-item", {
      has: this.page.getByText(label, { exact: true }),
    });
    await card.getByRole("button", { name: "Delete bookmark" }).click();
  }

  htmlPreviewButton() {
    return this.page.getByTestId("book-asset-html");
  }

  epubButton() {
    return this.page.getByTestId("book-asset-epub");
  }

  sendToKindleButton() {
    return this.page.getByTestId("book-send-to-kindle-button");
  }

  openReaderButton() {
    return this.page.getByTestId("book-open-reader-button");
  }
}

import { expect } from "../support/playwright";

export class AccessPageModel {
  constructor(page) {
    this.page = page;
    this.userSearchInput = page.locator(".access-users-search-field input");
    this.userStatusFilter = page
      .getByTestId("access-users-section")
      .locator('select')
      .first();
    this.userForm = page.getByTestId("access-user-form");
    this.usersTable = page.getByTestId("access-users-table");
    this.accessRulesForm = page.getByTestId("access-grant-form");
    this.accessRulesTable = page.getByTestId("access-rules-table");
  }

  async goto() {
    await this.page.goto("/access");
    await expect(
      this.page.getByRole("heading", { name: "Users & Access" }),
    ).toBeVisible();
    await expect(this.usersTable).toBeVisible();
  }

  async searchUsers(query) {
    await this.userSearchInput.fill(query);
  }

  async filterUsersByStatus(status) {
    await this.userStatusFilter.selectOption(status);
  }

  async editUserByEmail(email) {
    const row = this.usersTable
      .locator("tbody tr")
      .filter({ has: this.page.getByText(email) });
    await row.getByRole("button", { name: "Edit" }).click();
    await expect(this.userForm).toBeVisible();
  }

  async setRequireTwoFactor(enabled = true) {
    const checkbox = this.page.getByRole("checkbox", {
      name: "Require Two-Factor",
    });
    if (enabled) {
      await checkbox.check();
    } else {
      await checkbox.uncheck();
    }
  }

  async saveUser() {
    await this.userForm.getByRole("button", { name: "Save User" }).click();
    await expect(this.page.getByText("User updated.")).toBeVisible();
  }

  async switchToAccessRules() {
    await this.page.getByTestId("access-rules-tab").click();
    await expect(this.accessRulesForm).toBeVisible();
  }

  async selectGrantUser(userId) {
    await this.accessRulesForm.locator("select").first().selectOption(userId);
  }

  async selectGrantUserByLabel(label) {
    await this.accessRulesForm.locator("select").first().selectOption({
      label,
    });
  }

  async toggleGrantPermission(label) {
    const checkbox = this.accessRulesForm.getByRole("checkbox", {
      name: label,
    });
    await checkbox.check();
  }

  async chooseGrantTargetType(label) {
    await this.accessRulesForm.getByRole("button", { name: label }).click();
  }

  async searchTargets(query) {
    await this.accessRulesForm
      .locator('input[type="search"]')
      .fill(query);
  }

  async toggleTarget(label) {
    const checkbox = this.accessRulesForm.getByRole("checkbox", {
      name: label,
    });
    await checkbox.check();
  }

  async saveAccessRule() {
    await this.accessRulesForm.getByRole("button", { name: "Save Access" }).click();
  }
}

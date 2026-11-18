import { expect, test } from "./support/playwright";
import { AccessPageModel } from "./pages/accessPage";
import { loginAsSuperAdmin } from "./support/liveApp";
import { seedData } from "./support/seedData";

test.describe("Access Page", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page);
  });

  test("editing a user keeps the active list filters intact and persists the two-factor setting", async ({
    page,
  }) => {
    const accessPage = new AccessPageModel(page);

    await accessPage.goto();
    await accessPage.searchUsers("access-manager");
    await accessPage.filterUsersByStatus("active");
    await accessPage.editUserByEmail(seedData.accessUser.email);
    await accessPage.setRequireTwoFactor(true);
    await accessPage.saveUser();

    await expect(accessPage.userSearchInput).toHaveValue("access-manager");
    await expect(accessPage.userStatusFilter).toHaveValue("active");
    await expect(
      accessPage.usersTable.getByText(seedData.accessUser.email),
    ).toBeVisible();

    await page.reload();
    await accessPage.searchUsers("access-manager");
    await accessPage.editUserByEmail(seedData.accessUser.email);
    await expect(
      page.getByRole("checkbox", { name: "Require Two-Factor" }),
    ).toBeChecked();
  });

  test("creating a scoped book access rule shows the new rule in the live table", async ({
    page,
  }) => {
    const accessPage = new AccessPageModel(page);

    await accessPage.goto();
    await accessPage.switchToAccessRules();
    await accessPage.selectGrantUserByLabel(seedData.accessUser.email);
    await accessPage.toggleGrantPermission("Edit metadata");
    await accessPage.chooseGrantTargetType("Books");
    await accessPage.searchTargets("Access Grant");
    await accessPage.toggleTarget(seedData.books.access.title);
    await accessPage.saveAccessRule();

    await expect(
      accessPage.accessRulesTable.getByText(seedData.books.access.title),
    ).toBeVisible();
    await expect(
      accessPage.accessRulesTable.getByText(seedData.accessUser.email),
    ).toBeVisible();
  });
});

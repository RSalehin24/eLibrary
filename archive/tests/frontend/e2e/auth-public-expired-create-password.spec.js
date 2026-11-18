import { expect, test } from "./support/playwright";
import { AuthPageModel } from "./pages/authPage";

test.describe("Public Auth Expired Create Password Links", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("expired create password links render the expired state instead of the form", async ({
    page,
  }) => {
    const authPage = new AuthPageModel(page);
    let validateCount = 0;
    let confirmCount = 0;

    await page.route("**/api/auth/session/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ authenticated: false, user: null }),
      });
    });
    await page.route("**/api/csrf/", async (route) => {
      await route.fulfill({ status: 204, body: "" });
    });
    await page.route("**/api/auth/password-reset/validate/", async (route) => {
      validateCount += 1;
      if (validateCount === 1) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            detail: "Password link is valid.",
          }),
        });
        return;
      }

      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Reset token is invalid or expired.",
        }),
      });
    });
    await page.route("**/api/auth/password-reset/confirm/", async (route) => {
      confirmCount += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Password reset complete.",
          next_step: "login",
        }),
      });
    });

    await authPage.gotoCreatePasswordLink("single-use-uid", "single-use-token");
    await expect(page.locator("header.topbar .session-box")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Sign in" })).toHaveCount(0);
    await authPage.fillResetPasswords("strong-password-456");
    await authPage.submitPasswordReset();

    await expect(page).toHaveURL(/\/login/);

    await page.goto("/create-password?uid=single-use-uid&token=single-use-token");

    expect(confirmCount).toBe(1);
    await expect(
      page.getByRole("heading", { name: "The link has been expired" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Create password" }),
    ).toHaveCount(0);
  });
});

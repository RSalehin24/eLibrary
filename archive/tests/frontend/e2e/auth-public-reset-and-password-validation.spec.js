import { expect, test } from "./support/playwright";
import { AuthPageModel } from "./pages/authPage";

test.describe("Public Auth Reset Link And Password Validation Pages", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("expired reset password links render the expired state instead of the form", async ({
    page,
  }) => {
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
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Reset token is invalid or expired.",
        }),
      });
    });

    await page.goto("/reset-password/confirm?uid=expired-uid&token=expired-token");

    await expect(
      page.getByRole("heading", { name: "The link has expired" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Reset password" }),
    ).toHaveCount(0);
  });

  test("create password page shows a clean validation toast for short passwords", async ({
    page,
  }) => {
    const authPage = new AuthPageModel(page);

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
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Password link is valid.",
        }),
      });
    });
    await page.route("**/api/auth/password-reset/confirm/", async (route) => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Ensure this field has at least 12 characters.",
        }),
      });
    });

    await authPage.gotoCreatePasswordLink("invite-uid", "invite-token");
    await authPage.fillResetPasswords("short");
    await authPage.submitPasswordReset();

    const errorToast = page.getByRole("alert");
    await expect(errorToast.getByText("Something went wrong")).toBeVisible();
    await expect(
      errorToast.getByText("Ensure this field has at least 12 characters."),
    ).toBeVisible();
  });
});

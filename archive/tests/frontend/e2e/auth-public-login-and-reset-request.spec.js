import { expect, test } from "./support/playwright";
import { AuthPageModel } from "./pages/authPage";

test.describe("Public Auth Login And Reset Request Pages", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("login page does not request processing state or show restart/auth toasts", async ({
    page,
  }) => {
    const authPage = new AuthPageModel(page);
    let processingStateRequests = 0;

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
    await page.route("**/api/processing/state/", async (route) => {
      processingStateRequests += 1;
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Authentication credentials were not provided.",
        }),
      });
    });

    await authPage.gotoLogin();
    await page.waitForTimeout(250);

    expect(processingStateRequests).toBe(0);
    await expect(
      page
        .getByRole("status")
        .filter({ hasText: "The application has restarted. Please log in again." }),
    ).toHaveCount(0);
    await expect(
      page
        .getByRole("alert")
        .filter({ hasText: "Authentication credentials were not provided." }),
    ).toHaveCount(0);
  });

  test("sign in requires complete credentials and shows live email feedback", async ({
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

    await authPage.gotoLogin();

    const continueButton = page.getByRole("button", { name: "Continue" });
    await expect(page.locator(".login-email-feedback")).toHaveCount(0);
    await expect(continueButton).toBeDisabled();

    await authPage.emailInput().fill("reader");
    await expect(page.locator(".login-email-feedback-invalid")).toBeVisible();
    await expect(page.getByText("Enter a valid email address.")).toBeVisible();
    await expect(continueButton).toBeDisabled();

    await authPage.passwordInput().fill("strong-password-123");
    await expect(continueButton).toBeDisabled();

    await authPage.emailInput().fill("reader@example.com");
    await expect(page.locator(".login-email-feedback-valid")).toBeVisible();
    await expect(page.getByText("Email looks good.")).toBeVisible();
    await expect(continueButton).toBeEnabled();
  });

  test("reset password page validates email format before requesting a reset email", async ({
    page,
  }) => {
    const authPage = new AuthPageModel(page);
    let resolveResetRequest;
    const resetRequestPromise = new Promise((resolve) => {
      resolveResetRequest = resolve;
    });

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
    await page.route("**/api/auth/password-reset/", async (route) => {
      resolveResetRequest(JSON.parse(route.request().postData() || "{}"));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Reset email has been sent.",
        }),
      });
    });

    await authPage.gotoPasswordResetRequest();
    const resetButton = page.getByRole("button", { name: "Reset Password" });

    await expect(resetButton).toBeDisabled();
    await authPage.fillPasswordResetRequestEmail("reader");
    await expect(page.locator(".login-email-feedback-invalid")).toBeVisible();
    await expect(page.getByText("Enter a valid email address.")).toBeVisible();
    await expect(resetButton).toBeDisabled();

    await expect(
      page.getByText(
        "Enter your email address and we'll send you a secure password reset link.",
      ),
    ).toHaveCount(0);
    await authPage.fillPasswordResetRequestEmail("reader@example.com");
    await expect(page.locator(".login-email-feedback-valid")).toBeVisible();
    await expect(page.getByText("Email looks good.")).toBeVisible();
    await expect(resetButton).toBeEnabled();
    await authPage.submitPasswordResetRequest();

    expect(await resetRequestPromise).toEqual({ email: "reader@example.com" });
    await expect(page.getByText("Reset email has been sent.")).toBeVisible();
  });

  test("reset password page shows the missing-user message without extra copy", async ({
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
    await page.route("**/api/auth/password-reset/", async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "No user exist with this email.",
        }),
      });
    });

    await authPage.gotoPasswordResetRequest();
    await authPage.fillPasswordResetRequestEmail("missing@example.com");
    await authPage.submitPasswordResetRequest();

    await expect(page.getByText("No user exist with this email.")).toBeVisible();
  });
});

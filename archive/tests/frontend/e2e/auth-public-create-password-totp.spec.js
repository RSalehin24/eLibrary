import { expect, test } from "./support/playwright";
import { AuthPageModel } from "./pages/authPage";

test.describe("Public Auth Create Password Two Factor Flow", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("create password confirmation sends required users into the forced two-factor setup flow", async ({
    page,
  }) => {
    const authPage = new AuthPageModel(page);
    let resolveConfirmRequest;
    const confirmRequestPromise = new Promise((resolve) => {
      resolveConfirmRequest = resolve;
    });
    let sessionPayload = {
      authenticated: false,
      user: null,
    };

    await page.route("**/api/auth/session/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionPayload),
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
      resolveConfirmRequest(JSON.parse(route.request().postData() || "{}"));
      sessionPayload = {
        authenticated: true,
        user: {
          id: 77,
          email: "invitee@example.com",
          full_name: "Invitee User",
          profile_image_url: "",
          is_active: true,
          is_staff: false,
          is_superuser: false,
          totp_enabled: false,
          totp_required: true,
          totp_setup_required: true,
          capabilities: [],
        },
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Password saved. Continue with two-factor setup.",
          next_step: "totp_setup",
          user: sessionPayload.user,
        }),
      });
    });
    await page.route("**/api/auth/2fa/setup/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          provisioning_uri: "otpauth://totp/Bangla%20Library:invitee@example.com",
          secret: "ABC123XYZ789",
          qr_svg:
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='#ffffff'/><rect x='20' y='20' width='60' height='60' fill='#123f33'/></svg>",
        }),
      });
    });

    await authPage.gotoCreatePasswordLink("invite-uid", "invite-token");
    await expect(page.locator("header.topbar")).toHaveCount(1);
    await expect(page.locator("header.topbar.topbar-public")).toHaveCount(1);
    await expect(page.locator("header.topbar .session-box")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Sign in" })).toHaveCount(0);
    await authPage.fillResetPasswords("strong-password-456");
    await authPage.submitPasswordReset();

    expect(await confirmRequestPromise).toEqual({
      uid: "invite-uid",
      token: "invite-token",
      new_password: "strong-password-456",
    });
    await expect(
      page.getByText(
        "Password created. Set up two-factor authentication to continue.",
      ),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/two-factor-setup/);
    await expect(
      page.getByRole("heading", { name: "Set up two-factor authentication" }),
    ).toBeVisible();
    await expect(page.locator("header.topbar")).toHaveCount(1);
    await expect(page.locator("header.topbar.topbar-public")).toHaveCount(1);
    await expect(page.locator("header.topbar .topnav")).toHaveCount(0);
    await expect(page.locator("header.topbar .session-box")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "My Books" })).toHaveCount(0);
    await expect(page.locator("header.topbar .profile-menu-trigger")).toHaveCount(0);
    await expect(page.locator("section.auth-setup-card.login-card")).toBeVisible();
    await expect(
      page.getByText(
        "Your administrator requires an authenticator app before you can use the rest of Bangla Library.",
      ),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Verify and Continue" }),
    ).toBeVisible();
  });
});

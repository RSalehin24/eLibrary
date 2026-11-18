import { expect, test } from "./support/playwright";
import { AuthPageModel } from "./pages/authPage";

test.describe("Public Auth Forced Two Factor Setup Gate", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("required users are redirected away from protected pages into the setup gate", async ({
    page,
  }) => {
    const sessionPayload = {
      authenticated: true,
      user: {
        id: 88,
        email: "forced-setup@example.com",
        full_name: "Forced Setup",
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
    await page.route("**/api/auth/2fa/setup/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          provisioning_uri:
            "otpauth://totp/Bangla%20Library:forced-setup@example.com",
          secret: "FORCED123456",
          qr_svg:
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='#ffffff'/><circle cx='50' cy='50' r='24' fill='#123f33'/></svg>",
        }),
      });
    });

    await page.goto("/home");

    await expect(page).toHaveURL(/\/two-factor-setup/);
    await expect(page.locator("header.topbar")).toHaveCount(1);
    await expect(page.locator("header.topbar.topbar-public")).toHaveCount(1);
    await expect(page.locator("header.topbar .topnav")).toHaveCount(0);
    await expect(page.locator("header.topbar .session-box")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "My Books" })).toHaveCount(0);
    await expect(page.locator("header.topbar .profile-menu-trigger")).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Set up two-factor authentication" }),
    ).toBeVisible();
    await expect(page.locator("section.auth-setup-card.login-card")).toBeVisible();
  });
});

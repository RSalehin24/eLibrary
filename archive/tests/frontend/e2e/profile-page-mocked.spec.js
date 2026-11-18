import { expect, test } from "./support/playwright";

const profilePayload = {
  id: 1,
  email: "profile-user@example.com",
  full_name: "Profile User",
  profile_image_url: "",
  kindle_emails: ["reader@kindle.com"],
  kindle_sender_email: "library-sender@example.com",
  is_active: true,
  is_staff: false,
  is_superuser: false,
};

function sessionPayload({ totpEnabled = false, profile = profilePayload } = {}) {
  return {
    authenticated: true,
    user: {
      ...profile,
      totp_enabled: totpEnabled,
      totp_required: false,
      totp_setup_required: false,
      capabilities: [],
    },
  };
}

function twoFactorStatus({ enabled = false, pendingSetup = false } = {}) {
  return {
    enabled,
    pending_setup: pendingSetup,
    required: false,
    setup_required: false,
  };
}

async function installProfileRoutes(page, options = {}) {
  const { profile: profileOverrides = {} } = options;
  let totpEnabled = false;
  let pendingSetup = false;
  let currentProfile = { ...profilePayload, ...profileOverrides };

  await page.route("**/api/csrf/", async (route) => {
    await route.fulfill({ status: 204, body: "" });
  });
  await page.route("**/api/auth/session/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload({ totpEnabled, profile: currentProfile })),
    });
  });
  await page.route("**/api/auth/profile/", async (route) => {
    if (route.request().method() === "PATCH") {
      const postData = route.request().postDataBuffer();
      const requestBody = postData ? postData.toString("utf-8") : "";
      const match = requestBody.match(
        /name="kindle_emails_text"\r\n\r\n([\s\S]*?)\r\n--/,
      );
      if (match) {
        currentProfile = {
          ...currentProfile,
          kindle_emails: match[1]
            .split(/\r?\n/)
            .map((value) => value.trim())
            .filter(Boolean),
        };
      }
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(currentProfile),
    });
  });
  await page.route("**/api/auth/2fa/status/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        twoFactorStatus({ enabled: totpEnabled, pendingSetup }),
      ),
    });
  });
  await page.route("**/api/auth/2fa/setup/", async (route) => {
    pendingSetup = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        provisioning_uri:
          "otpauth://totp/RSalehin24%20Library:profile-user@example.com",
        secret: "ABCDEF123456",
        qr_svg: "<svg viewBox=\"0 0 10 10\"><rect width=\"10\" height=\"10\" /></svg>",
      }),
    });
  });
  await page.route("**/api/auth/2fa/cancel/", async (route) => {
    pendingSetup = false;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Pending TOTP setup canceled." }),
    });
  });
  await page.route("**/api/auth/2fa/confirm/", async (route) => {
    const body = JSON.parse(route.request().postData() || "{}");
    if (body.token === "000000") {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid TOTP token." }),
      });
      return;
    }

    totpEnabled = true;
    pendingSetup = false;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ detail: "TOTP is now enabled." }),
    });
  });
}

async function openProfileEditor(page) {
  await page.goto("/profile");
  await expect(
    page.getByRole("heading", { name: "Profile", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit" }).click();
  await expect(
    page.getByRole("heading", { name: "Two-Factor Authentication" }),
  ).toBeVisible();
}

test.describe("Profile Page TOTP Notifications", () => {
  test("alerts toggle is shown in the profile dropdown and persists locally", async ({
    page,
  }) => {
    await installProfileRoutes(page);
    await page.goto("/");
    await page.evaluate(() => {
      window.localStorage.removeItem("app.notifications.muted");
    });

    await page.goto("/profile");
    await expect(
      page.getByRole("heading", { name: "Profile", exact: true }),
    ).toBeVisible();

    await page.getByTestId("profile-menu-trigger").click();
    await expect(page.getByTestId("profile-alerts-toggle")).toBeChecked();
    await page.getByTestId("profile-alerts-toggle").click();
    await expect(page.getByTestId("profile-alerts-toggle")).not.toBeChecked();

    await page.reload();

    await expect(
      page.getByRole("heading", { name: "Profile", exact: true }),
    ).toBeVisible();
    await page.getByTestId("profile-menu-trigger").click();
    await expect(page.getByTestId("profile-alerts-toggle")).not.toBeChecked();
  });

  test("setup and cancel do not create toast notifications", async ({ page }) => {
    await installProfileRoutes(page);
    await openProfileEditor(page);

    await page.getByRole("button", { name: "Setup Authenticator" }).click();
    await expect(
      page.getByRole("heading", { name: "Authenticator Setup" }),
    ).toBeVisible();
    await expect(page.locator(".toast")).toHaveCount(0);

    await page.getByRole("button", { name: "Cancel Setup" }).click();
    await expect(
      page.getByRole("heading", { name: "Authenticator Setup" }),
    ).toHaveCount(0);
    await expect(page.locator(".toast")).toHaveCount(0);
  });

  test("verify still reports success and token errors", async ({ page }) => {
    await installProfileRoutes(page);
    await openProfileEditor(page);

    await page.getByRole("button", { name: "Setup Authenticator" }).click();
    await page.getByLabel("Verification Code").fill("000000");
    await page.getByRole("button", { name: "Verify and Enable" }).click();
    await expect(page.getByRole("alert")).toContainText("Invalid TOTP token.");

    await page.getByLabel("Dismiss notification").click();
    await page.getByLabel("Verification Code").fill("123456");
    await page.getByRole("button", { name: "Verify and Enable" }).click();
    await expect(page.getByRole("status")).toContainText("Two-factor enabled.");
  });

  test("kindle mails can be edited from the collapsed profile section", async ({
    page,
  }) => {
    await installProfileRoutes(page);
    await openProfileEditor(page);

    const kindleSection = page
      .getByRole("heading", { name: "Kindle Mails" })
      .locator("xpath=ancestor::section[1]");

    await kindleSection.getByRole("button", { name: "Expand" }).click();
    await expect(kindleSection).toContainText("library-sender@example.com");
    await expect(kindleSection).toContainText("Personal Document Settings");
    await page.getByLabel("Kindle Email 1").fill("reader@kindle.com");
    await page.getByRole("button", { name: "Add Kindle Email" }).click();
    await page.getByLabel("Kindle Email 2").fill("shared@kindle.com");
    await page.getByRole("button", { name: "Save Changes" }).click();

    await expect(page.locator(".toast")).toContainText("Profile updated.");
    await expect(page.getByText("reader@kindle.com", { exact: true })).toBeVisible();
    await expect(page.getByText("shared@kindle.com")).toBeVisible();
  });

  test("kindle mails require a valid Kindle address before another field can be added", async ({
    page,
  }) => {
    await installProfileRoutes(page, {
      profile: {
        kindle_emails: [],
      },
    });
    await openProfileEditor(page);

    const kindleSection = page
      .getByRole("heading", { name: "Kindle Mails" })
      .locator("xpath=ancestor::section[1]");
    const addButton = page.getByRole("button", { name: "Add Kindle Email" });

    await kindleSection.getByRole("button", { name: "Expand" }).click();
    await expect(addButton).toBeDisabled();

    await page.getByLabel("Kindle Email 1").fill("reader");
    await expect(page.getByText("Enter a valid email address.")).toBeVisible();
    await expect(addButton).toBeDisabled();

    await page.getByLabel("Kindle Email 1").fill("reader@example.com");
    await expect(
      page.getByText(
        "Use a Kindle email ending in @kindle.com.",
      ),
    ).toBeVisible();
    await expect(addButton).toBeDisabled();

    await page.getByLabel("Kindle Email 1").fill("reader@kindle.com");
    await expect(page.getByText("Kindle email looks good.")).toBeVisible();
    await expect(addButton).toBeEnabled();

    await addButton.click();
    await expect(page.getByLabel("Kindle Email 2")).toBeVisible();
    await expect(addButton).toBeDisabled();
  });
});

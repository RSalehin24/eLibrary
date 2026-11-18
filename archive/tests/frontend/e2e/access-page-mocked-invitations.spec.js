import { expect, test } from "./support/playwright";
import { createManagedUsersPayload, createReferencesPayload, createSessionPayload } from "./access-page-mocked/accessPageMocks.js";

test.describe("Access Page Invitation Notifications", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("creating an invited user shows a minimal setup-email notification", async ({
    page,
  }) => {
    let resolveCreateRequest;
    const createRequestPromise = new Promise((resolve) => {
      resolveCreateRequest = resolve;
    });
    let usersPayload = [
      {
        id: 1,
        email: "superadmin@example.com",
        full_name: "Super Admin",
        is_active: true,
        is_superuser: true,
        totp_required: false,
        global_scopes: ["admin:access"],
        grant_count: 0,
        can_resend_setup_email: false,
      },
    ];

    await page.route("**/api/auth/session/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(createSessionPayload()),
      });
    });
    await page.route("**/api/csrf/", async (route) => {
      await route.fulfill({ status: 204, body: "" });
    });
    await page.route("**/api/auth/users/**", async (route) => {
      if (route.request().method() === "POST") {
        resolveCreateRequest(JSON.parse(route.request().postData() || "{}"));
        usersPayload = [
          ...usersPayload,
          {
            id: 77,
            email: "invited@example.com",
            full_name: "Invited User",
            is_active: true,
            totp_required: true,
            global_scopes: ["read:durable"],
            grant_count: 0,
            can_resend_setup_email: true,
          },
        ];
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            email: "invited@example.com",
            full_name: "Invited User",
            is_active: true,
            totp_required: true,
            global_scopes: ["read:durable"],
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          createManagedUsersPayload(route.request().url(), usersPayload),
        ),
      });
    });
    await page.route("**/api/access/grants/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/api/access/references/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          createReferencesPayload([
            {
              value: "read:durable",
              label: "Read durable books",
            },
          ]),
        ),
      });
    });

    await page.goto("/access");

    const userForm = page.getByTestId("access-user-form");
    await expect(userForm).toBeVisible();

    await userForm.locator('input[placeholder="Full name"]').fill("Invited User");
    await userForm.locator('input[type="email"]').fill("invited@example.com");
    await page.getByRole("checkbox", { name: "Require Two-Factor" }).check();
    await page.getByRole("checkbox", { name: "Read durable books" }).check();
    await userForm.getByRole("button", { name: "Create User" }).click();

    expect(await createRequestPromise).toEqual({
      email: "invited@example.com",
      full_name: "Invited User",
      is_active: true,
      totp_required: true,
      send_invite_email: true,
      global_scopes: ["read:durable"],
    });
    await expect(page.getByText("User created. Setup email sent.")).toBeVisible();
  });

  test("pending invited users show a resend-email action in the users list", async ({
    page,
  }) => {
    const usersPayload = [
      {
        id: 1,
        email: "superadmin@example.com",
        full_name: "Super Admin",
        is_active: true,
        is_superuser: true,
        totp_required: false,
        global_scopes: ["admin:access"],
        grant_count: 0,
        can_resend_setup_email: false,
      },
      {
        id: 77,
        email: "pending@example.com",
        full_name: "Pending User",
        is_active: true,
        is_superuser: false,
        totp_required: true,
        totp_enabled: false,
        global_scopes: ["read:durable"],
        grant_count: 0,
        can_resend_setup_email: true,
      },
    ];

    await page.route("**/api/auth/session/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(createSessionPayload()),
      });
    });
    await page.route("**/api/csrf/", async (route) => {
      await route.fulfill({ status: 204, body: "" });
    });
    await page.route("**/api/auth/users/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          createManagedUsersPayload(route.request().url(), usersPayload),
        ),
      });
    });
    await page.route("**/api/access/grants/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/api/access/references/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          createReferencesPayload([
            {
              value: "read:durable",
              label: "Read durable books",
            },
          ]),
        ),
      });
    });

    await page.goto("/access");

    await expect(
      page
        .locator("tr", { hasText: "pending@example.com" })
        .getByRole("button", { name: "Resend Email" }),
    ).toBeVisible();
    await expect(
      page
        .locator("tr", { hasText: "pending@example.com" })
        .getByRole("button", { name: "Edit" }),
    ).toBeVisible();
    await expect(
      page.locator("tr", { hasText: "superadmin@example.com" }).getByText("Locked"),
    ).toBeVisible();
  });
});

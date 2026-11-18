import { expect, test } from "./support/playwright";
import { createManagedUsersPayload, createReferencesPayload, createSessionPayload } from "./access-page-mocked/accessPageMocks.js";

test.describe("Access Page Permission Chips", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("users list renders each account permission as a separate chip", async ({
    page,
  }) => {
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
          createManagedUsersPayload(route.request().url(), [
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
              email: "permissions@example.com",
              full_name: "Permission User",
              is_active: true,
              is_superuser: false,
              totp_required: false,
              global_scopes: ["metadata:edit", "read:durable"],
              grant_count: 0,
              can_resend_setup_email: false,
            },
          ]),
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
            {
              value: "metadata:edit",
              label: "Edit metadata",
            },
          ]),
        ),
      });
    });

    await page.goto("/access");

    const permissionRow = page.locator("tr", {
      has: page.getByText("permissions@example.com"),
    });
    const chips = permissionRow.locator(".access-permission-chip");

    await expect(chips).toHaveCount(2);
    await expect(permissionRow.getByText("Edit metadata")).toBeVisible();
    await expect(permissionRow.getByText("Read durable books")).toBeVisible();
  });
});

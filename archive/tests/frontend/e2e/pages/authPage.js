import { expect } from "../support/playwright";

export class AuthPageModel {
  constructor(page) {
    this.page = page;
  }

  async gotoLogin() {
    await this.page.goto("/login");
    await expect(
      this.page.getByRole("heading", { name: "Sign in" }),
    ).toBeVisible();
  }

  async gotoPasswordResetLink(uid = "reset-user", token = "reset-token") {
    await this.page.goto(`/reset-password/confirm?uid=${uid}&token=${token}`);
    await expect(
      this.page.getByRole("heading", { name: "New password" }),
    ).toBeVisible();
  }

  async gotoPasswordResetRequest() {
    await this.page.goto("/reset-password");
    await expect(
      this.page.getByRole("heading", { name: "Reset your password" }),
    ).toBeVisible();
  }

  async gotoCreatePasswordLink(uid = "invite-user", token = "invite-token") {
    await this.page.goto(`/create-password?uid=${uid}&token=${token}`);
    await expect(
      this.page.getByRole("heading", { name: "Create password" }),
    ).toBeVisible();
  }

  emailInput() {
    return this.page.getByLabel("Email");
  }

  passwordInput() {
    return this.page
      .locator("label", { hasText: "Password" })
      .locator("input")
      .first();
  }

  otpInput() {
    return this.page.getByLabel("TOTP code");
  }

  async fillCredentials({ email, password }) {
    await this.emailInput().fill(email);
    await this.passwordInput().fill(password);
  }

  async fillPasswordResetRequestEmail(email) {
    await this.emailInput().fill(email);
  }

  async submitLogin() {
    const backendStatusOverlay = this.page.locator(".backend-status-overlay");
    let forceClick = false;
    if (await backendStatusOverlay.count()) {
      try {
        await expect(backendStatusOverlay).toBeHidden({ timeout: 5_000 });
      } catch {
        forceClick = true;
      }
    }

    await this.page
      .getByRole("button", { name: /Continue|Verify/ })
      .click({ force: forceClick });
  }

  async fillResetPasswords(password) {
    await this.page
      .locator("label", { hasText: "New password" })
      .locator("input")
      .first()
      .fill(password);
    await this.page
      .locator("label", { hasText: "Confirm password" })
      .locator("input")
      .first()
      .fill(password);
  }

  async submitPasswordReset() {
    await this.page
      .getByRole("button", { name: /Reset password|Create password/ })
      .click();
  }

  async submitPasswordResetRequest() {
    await this.page.getByRole("button", { name: "Reset Password" }).click();
  }
}

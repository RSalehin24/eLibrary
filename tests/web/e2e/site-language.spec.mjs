import { test, expect, useAccount, setLanguage } from "./fixtures.mjs";

test("English and Bengali persist across public pages and preserve typed sign-in values", async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("ইমেইল", { exact: true }).fill("language-check@example.test");
  await setLanguage(page, "en");
  await expect(page.getByRole("heading", { name: "Sign In to Your Account", exact: true })).toBeVisible();
  await expect(page).toHaveTitle("Sign In | Bangla Library");
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue("language-check@example.test");
  await expect(page.getByLabel("Two-Step Verification Code", { exact: true })).toHaveCount(0);
  for (const [path, heading] of [["/", "Find your next book"], ["/catalog/", "All Books"], ["/help/", "Using the Library"], ["/about/", "Stay connected to Bengali books"], ["/contact/", "Contact"], ["/reset-password/", "Forgot your password?"]]) {
    await page.goto(path); await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("heading", { level: 1, name: heading, exact: typeof heading === "string" })).toBeVisible();
    const labels = await page.locator('main label, main button, main nav, footer').evaluateAll(elements => elements.map(element => {
      const copy = element.cloneNode(true); copy.querySelectorAll('.brand-logo').forEach(logo => logo.remove()); return copy.textContent;
    }));
    expect(labels.filter(text => /[\u0980-\u09ff]/.test(text))).toEqual([]);
    await expect(page.locator('footer .brand-logo')).toHaveAccessibleName("বাংলা পাঠাগার");
  }
  await setLanguage(page, "bn"); await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "bn"); await expect(page.getByLabel("অ্যাকাউন্টের ইমেইল", { exact: true })).toBeVisible();
});

test("reader account pages and security controls use the same site language", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/profile/");
  await setLanguage(page, "en");
  await expect(page).toHaveTitle("Profile & Security | Bangla Library");
  await page.getByLabel("Name", { exact: true }).fill("A name that must survive switching");
  await setLanguage(page, "bn"); await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("A name that must survive switching");
  await setLanguage(page, "en");
  page.on("dialog", dialog => dialog.accept());
  for (const [path, heading] of [["/profile/", "Profile & Security"], ["/my-books/", "My Books"], ["/notes/", "Notes"], ["/kindle/", "Kindle Delivery Requests"]]) {
    await page.goto(path); await expect(page.getByRole("heading", { level: 1, name: heading, exact: true })).toBeVisible();
    const labels = await page.locator('main label, main button, main select option, main nav').allTextContents();
    expect(labels.filter(text => /[\u0980-\u09ff]/.test(text))).toEqual([]);
  }
  await page.reload(); await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("file selection and validation errors follow the language without resubmitting forms", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/profile/");
  const image = page.getByLabel("নতুন প্রোফাইলের ছবি", { exact: true });
  await image.setInputFiles({ name: "আমার-ছবি.png", mimeType: "image/png", buffer: Buffer.from("upload control test") });
  await expect(page.locator(".file-picker-name")).toHaveText("আমার-ছবি.png");
  await setLanguage(page, "en");
  await expect(page.locator(".file-picker-control")).toContainText("Choose File");
  expect(await page.getByLabel("New Profile Photo", { exact: true }).evaluate(input => input.files[0].name)).toBe("আমার-ছবি.png");
  let submissions = 0;
  await page.route("**/api/v1/auth/profile/", route => {
    if (route.request().method() !== "PATCH") return route.continue();
    submissions += 1; return route.fulfill({ status: 400, json: { code: "validation_error", field_errors: { current_password: ["Current password is incorrect."] } } });
  });
  await page.getByLabel("Current Password", { exact: true }).fill("test-current-password");
  await page.getByLabel("New Password", { exact: true }).fill("test-new-password");
  await page.getByLabel("Confirm New Password", { exact: true }).fill("test-new-password");
  await page.getByRole("button", { name: "Change Password", exact: true }).click();
  await expect(page.locator("#current_password-error")).toHaveText("Current password is incorrect.");
  await setLanguage(page, "bn");
  await expect(page.locator("#current_password-error")).toHaveText("বর্তমান পাসওয়ার্ডটি সঠিক নয়।");
  await expect(page.locator(".file-picker-control")).toContainText("ফাইল বেছে নিন");
  await expect(page.locator(".file-picker-name")).toHaveText("আমার-ছবি.png");
  expect(submissions).toBe(1);
});

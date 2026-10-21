import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../../../app/web/package.json", import.meta.url));
export const { test, expect } = require("playwright/test");
export const fixture = JSON.parse(readFileSync(process.env.FOUNDATION_FIXTURE_PATH, "utf8"));
export const canonicalOrigin = process.env.FOUNDATION_CANONICAL_ORIGIN ?? "http://127.0.0.1:3000";
export const artifactPath = name => fileURLToPath(new URL(`../../../test-artifacts/foundation/${name}`, import.meta.url));

export async function useAccount(page, account) {
  await page.context().addCookies([{ ...fixture[account].session,
    url: process.env.FOUNDATION_WEB_URL ?? "http://127.0.0.1:3000", httpOnly: true, sameSite: "Lax",
  }]);
}

export async function setLanguage(page, language) {
  const control = page.getByRole("button", { name: language === "en" ? "English" : "বাংলা", exact: true });
  const openedMenu = !await control.isVisible();
  if (openedMenu) await page.locator("details.account-menu:visible > summary").click();
  await control.click();
  if (openedMenu) await page.keyboard.press("Escape");
}

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(new URL("../../../app/web/package.json", import.meta.url));
export const { test, expect } = require("playwright/test");
export const fixture = JSON.parse(readFileSync(process.env.FOUNDATION_FIXTURE_PATH, "utf8"));
export const canonicalOrigin = process.env.FOUNDATION_CANONICAL_ORIGIN ?? "http://127.0.0.1:3000";

export async function useAccount(page, account) {
  await page.context().addCookies([{ ...fixture[account].session,
    url: process.env.FOUNDATION_WEB_URL ?? "http://127.0.0.1:3000", httpOnly: true, sameSite: "Lax",
  }]);
}

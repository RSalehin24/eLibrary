import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { getLiveBaseUrls, getRepoRoot, loadLocalEnv } from "./support/liveEnv";

const require = createRequire(
  new URL("../../../app/frontend/package.json", import.meta.url),
);
const { chromium } = require("playwright");

async function waitForUrl(url, timeoutMs = 120_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url, { redirect: "manual" });
      if (response.ok || response.status === 302 || response.status === 401) {
        return;
      }
    } catch {}

    try {
      const statusCode = execFileSync(
        "curl",
        [
          "-sS",
          "-o",
          "/dev/null",
          "-w",
          "%{http_code}",
          "--max-time",
          "5",
          url,
        ],
        {
          encoding: "utf8",
          stdio: ["ignore", "pipe", "ignore"],
        },
      ).trim();
      if (["200", "302", "401"].includes(statusCode)) {
        return;
      }
    } catch {}

    await delay(1000);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function writeSuperAdminStorageState({ frontend, repoRoot }) {
  const env = loadLocalEnv();
  const authStatePath = path.join(
    repoRoot,
    "tests/frontend/.auth/superadmin.json",
  );
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ baseURL: frontend });
  const page = await context.newPage();

  let lastError = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      await page.goto("/login", {
        waitUntil: "domcontentloaded",
        timeout: 30_000,
      });
      await page.getByLabel("Email").fill(
        env.SUPER_ADMIN_EMAIL || "admin@example.com",
      );
      await page
        .locator("label", { hasText: "Password" })
        .locator("input")
        .first()
        .fill(env.SUPER_ADMIN_PASSWORD || "changeme");
      await page.getByRole("button", { name: /Continue|Verify/ }).click();
      await Promise.race([
        page.waitForURL("**/home", { timeout: 15_000 }).catch(() => null),
        page
          .getByRole("heading", { name: "All Books" })
          .waitFor({
            state: "visible",
            timeout: 15_000,
          })
          .catch(() => null),
      ]);
      await page.goto("/home", { waitUntil: "domcontentloaded" });
      await page.getByRole("heading", { name: "All Books" }).waitFor({
        state: "visible",
        timeout: 15_000,
      });
      lastError = null;
      break;
    } catch (error) {
      lastError = error;
      await delay((attempt + 1) * 1000);
    }
  }

  if (lastError) {
    throw lastError;
  }

  fs.mkdirSync(path.dirname(authStatePath), { recursive: true });
  await context.storageState({ path: authStatePath });
  await browser.close();
}

function startDetachedStack({ env, repoRoot }) {
  const composeFile = path.join(repoRoot, "local/compose/docker-compose.yml");
  const services = "postgres redis backend worker processing-worker beat frontend";
  const command = [
    "set -euo pipefail",
    `if docker compose version >/dev/null 2>&1; then docker compose -f "${composeFile}" up -d --build ${services}; else docker-compose -f "${composeFile}" up -d --build ${services}; fi`,
  ].join("; ");

  execFileSync("bash", ["-lc", command], {
    cwd: repoRoot,
    env: { ...process.env, ...env },
    stdio: "inherit",
  });
}

export default async function globalSetup() {
  const env = loadLocalEnv();
  const repoRoot = getRepoRoot();
  const { frontend, backend } = getLiveBaseUrls();
  const backendSessionUrl = `${backend.replace(/\/$/, "")}/api/auth/session/`;

  if (process.env.PLAYWRIGHT_SKIP_STACK_START !== "1") {
    startDetachedStack({ env, repoRoot });
  }

  if (process.env.PLAYWRIGHT_SKIP_E2E_SEED !== "1") {
    execFileSync(path.join(repoRoot, "tests/scripts/seed-e2e-data.sh"), {
      cwd: repoRoot,
      stdio: "inherit",
    });
  }

  await writeSuperAdminStorageState({ frontend, repoRoot });
}

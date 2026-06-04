import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../../app/frontend/package.json", import.meta.url));
const { defineConfig } = require("playwright/test");

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
const configDir = path.dirname(fileURLToPath(import.meta.url));
const authStatePath = path.join(configDir, ".auth", "superadmin.json");

const runLiveProcessing = process.env.PLAYWRIGHT_RUN_LIVE_PROCESSING === "1";

export default defineConfig({
  testDir: "./e2e",
  testIgnore: runLiveProcessing ? [] : ["**/processing-pages-live*"],
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  globalSetup: "./e2e/globalSetup.js",
  use: {
    baseURL,
    storageState: authStatePath,
    trace: "on-first-retry",
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
      },
    },
  ],
});

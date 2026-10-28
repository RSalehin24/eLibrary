import { createRequire } from "node:module";

const require = createRequire(new URL("../../app/web/package.json", import.meta.url));
const { defineConfig, devices } = require("playwright/test");

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../../test-artifacts/foundation/browser",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: { baseURL: process.env.FOUNDATION_WEB_URL ?? "http://127.0.0.1:3000", screenshot: "only-on-failure", serviceWorkers: "block" },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
    { name: "firefox", use: { browserName: "firefox" } },
    { name: "webkit", use: { browserName: "webkit" } },
    { name: "android", use: { ...devices["Pixel 7"], browserName: "chromium" } },
    { name: "ios", use: { ...devices["iPhone 13"], browserName: "webkit" } },
  ],
});

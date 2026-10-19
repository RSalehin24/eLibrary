import { createRequire } from "node:module";

const require = createRequire(new URL("../../app/web/package.json", import.meta.url));
const { defineConfig, devices } = require("playwright/test");

const mobileJourneys = /(?:account-creation|book-details|notifications|book-exports|bulk-access|kindle-history|legacy-routes|queue-controls|catalog-filters|personal-notes|processing-clarity|catalog-usability|discovery|login|workspaces|personal-library|pwa|reader|reader-language|reader-legacy|reader-bookmark-precision|local-reader|uploads|jobs|book-lifecycle|admin-usability|admin-console|site-language|ux-workflows)\.spec\.mjs$/;

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
    { name: "android", testMatch: mobileJourneys, use: { ...devices["Pixel 7"], browserName: "chromium" } },
    { name: "ios", testMatch: mobileJourneys, use: { ...devices["iPhone 13"], browserName: "webkit" } },
  ],
});

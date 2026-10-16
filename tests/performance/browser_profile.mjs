import assert from "node:assert/strict";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import { fileURLToPath } from "node:url";
import { installLabObservers } from "./browser_metrics.mjs";

const require = createRequire(new URL("../../app/web/package.json", import.meta.url));
const { chromium, devices } = require("playwright");
const origin = "http://127.0.0.1:3000";
const outputRoot = new URL("../../test-artifacts/performance/", import.meta.url);
await mkdir(outputRoot, { recursive: true });
const artifacts = await mkdtemp(fileURLToPath(outputRoot) + "browser-lab-");

async function captureMetrics(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  return page.evaluate(() => {
    const navigation = performance.getEntriesByType("navigation")[0];
    const paint = performance.getEntriesByName("first-contentful-paint")[0];
    return { ...window.libraryLabMetrics, ttfb_ms: navigation.responseStart - navigation.requestStart, fcp_ms: paint?.startTime ?? null, transferred_bytes: navigation.transferSize };
  });
}

async function measure(browser, profile, path) {
  const context = await browser.newContext({ ...profile.device, serviceWorkers: "block" });
  try {
    await context.addInitScript(installLabObservers);
    const page = await context.newPage();
    const session = await context.newCDPSession(page);
    await session.send("Emulation.setCPUThrottlingRate", { rate: profile.cpuSlowdown });
    const response = await page.goto(origin + path, { waitUntil: "load" });
    assert.equal(response.status(), 200);
    await page.getByRole("heading", { level: 1 }).waitFor();
    const metrics = await captureMetrics(page);
    assert.ok(Number.isFinite(metrics.lcp_ms) && metrics.lcp_ms > 0, "LCP observation is required.");
    if (path === "/catalog/") await exerciseSearch(page);
    const interactions = await captureMetrics(page);
    await page.screenshot({ path: `${artifacts}/${profile.name}-${path === "/" ? "home" : "catalog"}-${profile.sample}.png` });
    return { profile: profile.name, path, cpu_slowdown: profile.cpuSlowdown, ...metrics, max_interaction_duration_ms: interactions.max_interaction_duration_ms };
  } finally { await context.close(); }
}

async function exerciseSearch(page) {
  const input = page.getByLabel("বই বা লেখকের নাম", { exact: true });
  await input.click();
  const found = page.waitForResponse((response) => new URL(response.url()).searchParams.get("q") === "pariksha" && response.status() === 200);
  await input.pressSequentially("pariksha", { delay: 60 });
  await found;
  await input.press("Tab");
}

const browser = await chromium.launch();
try {
  const profiles = [
    { name: "desktop", device: { viewport: { width: 1280, height: 800 } }, cpuSlowdown: 1 },
    { name: "android", device: devices["Pixel 7"], cpuSlowdown: 4 },
  ];
  const measurements = [];
  for (const profile of profiles) {
    for (const path of ["/", "/catalog/"]) {
      for (let sample = 0; sample < 3; sample += 1) measurements.push(await measure(browser, { ...profile, sample }, path));
    }
  }
  const report = {
    scope: "synthetic localhost browser timings; production Next frontend with development Django API; no WAN simulation",
    host: { architecture: os.arch(), cpu: os.cpus()[0].model, cores: os.cpus().length, memory_bytes: os.totalmem() },
    browser: browser.version(),
    limitation: "Observed load-window CLS and maximum Event Timing duration are lab observations; this is not field Web Vitals or an INP percentile.",
    measurements,
  };
  await writeFile(`${artifacts}/summary.json`, JSON.stringify(report, null, 2) + "\n", { flag: "wx", mode: 0o600 });
  console.log(`Browser lab passed ${measurements.length} observations; artifacts: ${artifacts}`);
} finally { await browser.close(); }

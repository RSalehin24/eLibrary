import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const origin = "https://library.example.test:18443";
const maximumUsers = 1000;
const maximumHoldSeconds = 3600;
const rampSeconds = 15;
const completionAllowanceSeconds = 60;
const targetUsers = Number(__ENV.CAPACITY_VUS ?? 5);
if (!Number.isInteger(targetUsers) || targetUsers < 1 || targetUsers > maximumUsers) {
  throw new Error("CAPACITY_VUS must be an integer between 1 and 1000.");
}
const holdSeconds = configuredHoldSeconds();
const fixture = loadFixture();
const publicLatency = new Trend("public_latency_ms", true);
const readingLatency = new Trend("reading_latency_ms", true);

function configuredHoldSeconds() {
  const match = /^(\d+)(s|m)$/.exec(__ENV.CAPACITY_HOLD ?? "20s");
  const seconds = match ? Number(match[1]) * (match[2] === "m" ? 60 : 1) : 0;
  if (seconds < 1 || seconds > maximumHoldSeconds) {
    throw new Error("CAPACITY_HOLD must be whole seconds or minutes between 1s and 60m.");
  }
  return seconds;
}

function fixtureSlug(value) {
  if (typeof value !== "string" || !value.trim() || value.length > 255) {
    throw new Error("Invalid fixture slug.");
  }
  return encodeURIComponent(value);
}

function loadFixture() {
  try {
    if (typeof __ENV.CAPACITY_FIXTURE_PATH !== "string" || !__ENV.CAPACITY_FIXTURE_PATH.trim()) {
      throw new Error("Missing fixture path.");
    }
    const values = JSON.parse(open(__ENV.CAPACITY_FIXTURE_PATH));
    const cookie = values?.reading_reader?.session;
    if (typeof cookie?.name !== "string" || typeof cookie?.value !== "string" || !/^[A-Za-z0-9_-]{1,256}$/.test(cookie.name) || !/^[A-Za-z0-9_-]{1,256}$/.test(cookie.value)) {
      throw new Error("Invalid fixture cookie.");
    }
    return { cookie, readingSlug: fixtureSlug(values.reading_book?.slug), publicSlug: fixtureSlug(values.public_book?.slug) };
  } catch {
    // Parser diagnostics can include fixture credentials; expose only a safe error.
    throw new Error("A valid private deployment fixture is required.");
  }
}

export const options = {
  stages: [
    { duration: "10s", target: targetUsers },
    { duration: `${holdSeconds}s`, target: targetUsers },
    { duration: "5s", target: 0 },
  ],
  thresholds: { checks: ["rate==1"], http_req_failed: ["rate<0.01"], iterations: ["count>0"] },
  systemTags: ["status", "method", "name", "scenario", "expected_response"],
  summaryTrendStats: ["med", "p(95)", "p(99)", "max", "count"],
  insecureSkipTLSVerify: false,
  noCookiesReset: false,
};

function requestOptions(name) {
  return { tags: { name }, redirects: 0, timeout: "15s" };
}

function setReaderCookie() {
  http.cookieJar().set(origin, fixture.cookie.name, fixture.cookie.value, { path: "/" });
}

function responseJSON(response, message) {
  try {
    return response.json();
  } catch {
    throw new Error(message);
  }
}

function authenticatedSession() {
  setReaderCookie();
  const response = http.get(`${origin}/api/v1/auth/session/`, requestOptions("setup_session"));
  if (response.status !== 200) throw new Error("Fixture session is unavailable.");
  const session = responseJSON(response, "Fixture session is unavailable.");
  if (session?.authenticated !== true || typeof session.csrf_token !== "string" || !/^[A-Za-z0-9_-]{1,256}$/.test(session.csrf_token)) {
    throw new Error("Fixture session is unavailable.");
  }
  return session;
}

function chapterPath(publication) {
  const base = publication?.resource_base;
  const path = publication?.chapters?.[0]?.path;
  if (typeof base !== "string" || !/^\/api\/v1\/reading\/sessions\/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\/resources\/$/.test(base) || typeof path !== "string") {
    throw new Error("Invalid chapter path.");
  }
  let decoded;
  try { decoded = decodeURIComponent(path); } catch { throw new Error("Invalid chapter path."); }
  const segments = decoded.split("/");
  if (/[\\%?#:\u0000-\u0020]/.test(decoded) || /%2f/i.test(path) || segments.some((segment) => !segment || segment === "." || segment === "..")) {
    throw new Error("Invalid chapter path.");
  }
  return base + segments.map(encodeURIComponent).join("/");
}

function requireSessionLifetime(publication) {
  const expires = Date.parse(publication?.expires_at);
  const requiredSeconds = rampSeconds + holdSeconds + completionAllowanceSeconds;
  if (!Number.isFinite(expires) || expires - Date.now() < requiredSeconds * 1000) {
    throw new Error("Fixture reading session expires before the workload ends.");
  }
}

export function setup() {
  const session = authenticatedSession();
  const launchOptions = requestOptions("setup_launch");
  launchOptions.headers = { "X-CSRFToken": session.csrf_token, Origin: origin, "Content-Type": "application/json" };
  const launch = http.post(`${origin}/api/v1/reading/books/${fixture.readingSlug}/launch/`, "{}", launchOptions);
  if (launch.status !== 200) throw new Error("Fixture reading access is unavailable.");
  const publication = responseJSON(launch, "Fixture reading access is unavailable.");
  const chapter = chapterPath(publication);
  requireSessionLifetime(publication);
  return { chapter };
}

function publicRead(path, name) {
  const response = http.get(origin + path, requestOptions(name));
  publicLatency.add(response.timings.duration);
  check(response, { "public response succeeds": (result) => result.status === 200 });
}

export default function capacityIteration(publication) {
  http.cookieJar().clear(origin);
  publicRead("/", "home_ssr");
  publicRead(`/books/${fixture.publicSlug}/`, "book_ssr");
  publicRead(`/api/v1/catalog/books/?q=${encodeURIComponent("পরীক্ষার বই")}`, "catalog_search");
  setReaderCookie();
  const chapter = http.get(origin + publication.chapter, requestOptions("protected_chapter"));
  readingLatency.add(chapter.timings.duration);
  check(chapter, { "protected chapter succeeds": (result) => result.status === 200 });
  sleep(1);
}

const metricNames = new Set([
  "checks", "checks_total", "checks_succeeded", "checks_failed",
  "http_reqs", "http_req_failed", "http_req_duration", "http_req_blocked",
  "http_req_connecting", "http_req_tls_handshaking", "http_req_sending", "http_req_waiting",
  "http_req_receiving", "iterations", "iteration_duration", "vus", "vus_max",
  "data_received", "data_sent", "public_latency_ms", "reading_latency_ms",
]);
const statisticNames = new Set(["count", "rate", "matches", "total", "passes", "fails", "value", "min", "max", "avg", "med", "p(95)", "p(99)"]);

function summaryMetric(metric) {
  const values = Object.fromEntries(Object.entries(metric.values ?? {}).filter(([key, value]) => statisticNames.has(key) && typeof value === "number" && Number.isFinite(value)));
  const thresholds = Object.fromEntries(Object.entries(metric.thresholds ?? {}).filter(([key, value]) => ["rate==1", "rate<0.01", "count>0"].includes(key) && typeof value?.ok === "boolean").map(([key, value]) => [key, { ok: value.ok }]));
  return { values, thresholds };
}

function summaryMetrics(data) {
  const entries = Array.isArray(data.results?.metrics)
    ? [...data.results.metrics, ...(data.results.checks?.metrics ?? [])].map((metric) => [metric.name, metric])
    : Object.entries(data.metrics ?? {});
  const metrics = entries.filter(([name]) => metricNames.has(name)).map(([name, metric]) => [name, summaryMetric(metric)]);
  if (!metrics.length) throw new Error("Capacity metrics are unavailable.");
  return Object.fromEntries(metrics);
}

export function handleSummary(data) {
  const report = {
    scope: "isolated HTTPS simulation; shared reader identity",
    target_users: targetUsers,
    hold_seconds: holdSeconds,
    duration_seconds: Number.isFinite(data.config?.duration) ? data.config.duration : undefined,
    application_hardware: __ENV.APPLICATION_HARDWARE ?? "unrecorded",
    load_generator_hardware: __ENV.LOAD_GENERATOR_HARDWARE ?? "unrecorded",
    metrics: summaryMetrics(data),
  };
  return { [__ENV.CAPACITY_REPORT ?? "capacity-summary.json"]: JSON.stringify(report, null, 2) + "\n" };
}

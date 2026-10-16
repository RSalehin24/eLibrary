import assert from "node:assert/strict";
import test from "node:test";
import { currentTime, fixture, loadHarness, origin, publication } from "./capacity-runtime.mjs";

test("capacity setup authenticates once and returns only a protected relative chapter", async () => {
  const { script, state } = await loadHarness();
  const result = script.setup();
  assert.deepEqual(JSON.parse(JSON.stringify(result)), { chapter: publication.resource_base + publication.chapters[0].path });
  assert.deepEqual(state.requests.map((request) => [request.method, request.options.tags.name]), [["GET", "setup_session"], ["POST", "setup_launch"]]);
  assert.equal(state.requests[1].options.headers["X-CSRFToken"], "synthetic-csrf-token");
  assert.equal(state.requests[1].options.headers.Origin, origin);
});

test("public reads stay anonymous when a VU retains cookies between iterations", async () => {
  const { script, state } = await loadHarness();
  const result = script.setup();
  state.requests.length = 0;
  script.default(result);
  script.default(result);
  assert.equal(state.requests.length, 8);
  assert.ok(state.requests.filter((request) => request.options.tags.name !== "protected_chapter").every((request) => !request.cookies.sessionid));
  assert.ok(state.requests.filter((request) => request.options.tags.name === "protected_chapter").every((request) => request.cookies.sessionid === fixture.reading_reader.session.value));
  assert.ok(state.requests.every((request) => request.method === "GET" && request.options.redirects === 0));
  assert.equal(state.trends.get("public_latency_ms").length, 6);
  assert.equal(state.trends.get("reading_latency_ms").length, 2);
});

test("failed public and protected requests remain failed checks", async () => {
  const { script, state } = await loadHarness();
  const result = script.setup();
  state.statuses.push(503, 200, 302, 403);
  script.default(result);
  assert.deepEqual(state.checks, [false, true, false, false]);
  assert.equal(script.options.insecureSkipTLSVerify, false);
  assert.deepEqual(Array.from(script.options.thresholds.checks), ["rate==1"]);
});

test("missing, malformed, and invalid fixture fields fail without echoing private input", async () => {
  for (const fixtureText of ["private-cookie-is-not-json", "null", "{}", JSON.stringify({ ...fixture, reading_book: { slug: "" } }), JSON.stringify({ ...fixture, reading_reader: { session: { name: "invalid\r\n", value: "private-cookie" } } }), JSON.stringify({ ...fixture, reading_reader: { session: { name: 123, value: 456 } } })]) {
    await assert.rejects(loadHarness({ fixtureText }), /A valid private deployment fixture is required\./);
  }
  await assert.rejects(loadHarness({ environment: { CAPACITY_FIXTURE_PATH: undefined } }), /A valid private deployment fixture is required\./);
});

test("unavailable and malformed sessions never launch reading", async () => {
  for (const session of [{ authenticated: "true", csrf_token: "token" }, { authenticated: false }, { authenticated: true }, { authenticated: true, csrf_token: "\r\n" }]) {
    const { script, state } = await loadHarness({ session });
    assert.throws(() => script.setup(), /Fixture session is unavailable\./);
    assert.equal(state.requests.length, 1);
  }
});

test("chapter path validation rejects traversal, query, fragments, and foreign resource bases", async () => {
  const chapters = ["../auth/session/", "%2e%2e/auth/session/", "%252e%252e/chapter.xhtml", "chapter.xhtml?token=private", "chapter.xhtml#private", "chapter\\private.xhtml", "//foreign.test/file", "folder/%2fchapter.xhtml"];
  for (const path of chapters) {
    const { script } = await loadHarness({ publication: { ...publication, chapters: [{ path }] } });
    assert.throws(() => script.setup(), /Invalid chapter path\./);
  }
  const { script } = await loadHarness({ publication: { ...publication, resource_base: "https://foreign.test/" } });
  assert.throws(() => script.setup(), /Invalid chapter path\./);
});

test("reading access must outlive the complete configured workload", async () => {
  for (const expires_at of ["invalid", new Date(currentTime - 1_000).toISOString(), new Date(currentTime + 30_000).toISOString()]) {
    const { script } = await loadHarness({ publication: { ...publication, expires_at } });
    assert.throws(() => script.setup(), /Fixture reading session expires before the workload ends\./);
  }
});

test("setup fails on denied sessions or unavailable publications without replay", async () => {
  const sessionRun = await loadHarness();
  sessionRun.state.statuses.push(403);
  assert.throws(() => sessionRun.script.setup(), /Fixture session is unavailable\./);
  assert.equal(sessionRun.state.requests.length, 1);
  const publicationRun = await loadHarness();
  publicationRun.state.statuses.push(200, 409);
  assert.throws(() => publicationRun.script.setup(), /Fixture reading access is unavailable\./);
  assert.equal(publicationRun.state.requests.length, 2);
});

test("invalid response JSON produces a sanitized error", async () => {
  for (const method of ["get", "post"]) {
    const { script, state } = await loadHarness();
    state.http[method] = () => ({ status: 200, json: () => { throw new Error("private-response-body"); } });
    assert.throws(() => script.setup(), (error) => /Fixture (session|reading access) is unavailable\./.test(error.message) && !error.message.includes("private-response-body"));
  }
});

test("configured duration and encoded chapter names remain usable", async () => {
  const { script } = await loadHarness({ environment: { CAPACITY_HOLD: "2m", CAPACITY_VUS: "12" }, publication: { ...publication, chapters: [{ path: "EPUB/অধ্যায়.xhtml" }] } });
  assert.equal(script.options.stages[1].duration, "120s");
  assert.equal(script.options.stages[1].target, 12);
  assert.equal(script.setup().chapter, publication.resource_base + "EPUB/" + encodeURIComponent("অধ্যায়.xhtml"));
});

test("invalid user counts and hold durations are rejected before requests", async () => {
  for (const value of ["0", "-1", "1.5", "1001", "bad", ""]) {
    await assert.rejects(loadHarness({ environment: { CAPACITY_VUS: value } }), /CAPACITY_VUS/);
  }
  for (const value of ["0s", "-1s", "1h", "3601s", "1.5s", "bad", ""]) {
    await assert.rejects(loadHarness({ environment: { CAPACITY_HOLD: value } }), /CAPACITY_HOLD/);
  }
});

test("summary retains measurements and threshold outcomes without private metric tags", async () => {
  const { script } = await loadHarness();
  const summary = script.handleSummary({ metrics: {
    http_reqs: { type: "counter", contains: "default", values: { count: 8, rate: 4 }, tags: { url: "private-session-url" } },
    public_latency_ms: { type: "trend", contains: "time", values: { med: 12, "p(95)": 20, "p(99)": 25, max: 30, count: 6 } },
    checks: { type: "rate", contains: "default", values: { rate: 0.75, passes: 3, fails: 1 }, thresholds: { "rate==1": { ok: false } } },
    "http_req_duration{url:private-session-url}": { values: { med: 12 } },
  } });
  const text = Object.values(summary)[0];
  assert.ok(!text.includes("private-session-url") && !text.includes(fixture.reading_reader.session.value));
  const report = JSON.parse(text);
  assert.equal(report.metrics.http_reqs.values.rate, 4);
  assert.equal(report.metrics.public_latency_ms.values["p(99)"], 25);
  assert.equal(report.metrics.checks.thresholds["rate==1"].ok, false);
  assert.equal(report.target_users, 5);
});

test("the k6 machine-readable summary preserves metrics and check counts", async () => {
  const { script } = await loadHarness();
  const summary = script.handleSummary({ version: "1.0.0", config: { duration: 35 }, results: {
    metrics: [
      { name: "http_reqs", type: "counter", contains: "default", values: { count: 100 } },
      { name: "reading_latency_ms", type: "trend", contains: "time", values: { med: 10, "p(95)": 30 } },
    ],
    checks: { metrics: [
      { name: "checks_total", type: "counter", contains: "default", values: { count: 100 } },
      { name: "checks_succeeded", type: "rate", contains: "default", values: { matches: 99, total: 100, rate: 0.99 } },
      { name: "checks_failed", type: "rate", contains: "default", values: { matches: 1, total: 100, rate: 0.01 } },
    ] },
  } });
  const report = JSON.parse(Object.values(summary)[0]);
  assert.equal(report.metrics.http_reqs.values.count, 100);
  assert.equal(report.metrics.reading_latency_ms.values["p(95)"], 30);
  assert.equal(report.metrics.checks_failed.values.matches, 1);
  assert.equal(report.metrics.checks_succeeded.values.total, 100);
  assert.equal(report.duration_seconds, 35);
});

test("an unrecognized summary format fails instead of writing an empty success report", async () => {
  const { script } = await loadHarness();
  assert.throws(() => script.handleSummary({ results: {} }), /Capacity metrics are unavailable\./);
});

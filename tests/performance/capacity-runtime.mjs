import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createContext, SourceTextModule, SyntheticModule } from "node:vm";

export const origin = "https://library.example.test:18443";
export const currentTime = 1_800_000_000_000;
export const fixture = {
  reading_reader: { session: { name: "sessionid", value: "synthetic-private-cookie" } },
  reading_book: { slug: "পড়ার-বই" },
  public_book: { slug: "প্রকাশিত-বই" },
};
export const publication = {
  resource_base: "/api/v1/reading/sessions/01234567-89ab-4cde-8fab-0123456789ab/resources/",
  chapters: [{ path: "EPUB/chapter-1.xhtml" }],
  expires_at: new Date(currentTime + 7_200_000).toISOString(),
};

function response(status, values = {}) {
  return { status, timings: { duration: 12 }, json: (key) => key ? values[key] : values };
}

function runtime() {
  const state = { requests: [], checks: [], trends: new Map(), cookies: new Map(), statuses: [] };
  const jar = {
    set: (_origin, name, value) => state.cookies.set(name, value),
    clear: () => state.cookies.clear(),
  };
  const record = (method, url, options) => {
    state.requests.push({ method, url, options, cookies: Object.fromEntries(state.cookies) });
    return state.statuses.shift() ?? 200;
  };
  state.http = {
    cookieJar: () => jar,
    get: (url, options) => response(record("GET", url, options), state.session),
    post: (url, _body, options) => response(record("POST", url, options), state.publication),
  };
  state.check = (value, checks) => {
    const outcomes = Object.values(checks).map((check) => check(value));
    state.checks.push(...outcomes);
    return outcomes.every(Boolean);
  };
  state.Trend = class {
    constructor(name) { this.samples = []; state.trends.set(name, this.samples); }
    add(value) { this.samples.push(value); }
  };
  return state;
}

export async function loadHarness(values = {}) {
  const state = runtime();
  state.session = values.session ?? { authenticated: true, csrf_token: "synthetic-csrf-token" };
  state.publication = values.publication ?? publication;
  const environment = { CAPACITY_FIXTURE_PATH: "/private/fixture.json", ...values.environment };
  const context = createContext({
    Date: class extends Date { static now() { return currentTime; } },
    __ENV: environment,
    open: (path) => {
      assert.equal(path, environment.CAPACITY_FIXTURE_PATH);
      return values.fixtureText ?? JSON.stringify(fixture);
    },
  });
  const modules = {
    "k6/http": { default: state.http },
    k6: { check: state.check, sleep: () => {} },
    "k6/metrics": { Trend: state.Trend },
  };
  const source = await readFile(new URL("./capacity.mjs", import.meta.url), "utf8");
  const script = new SourceTextModule(source, { context });
  await script.link((name) => {
    const exports = modules[name];
    assert.ok(exports, `Unexpected capacity runtime import: ${name}`);
    return new SyntheticModule(Object.keys(exports), function () {
      for (const [key, value] of Object.entries(exports)) this.setExport(key, value);
    }, { context });
  });
  await script.evaluate();
  return { script: script.namespace, state };
}

import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { workspaceSessionForCookies } = await typescriptModule(new URL("../../../app/web/src/lib/public-session.ts", import.meta.url));

test("a public static shell needs no API and never invents authenticated or management access", async () => {
  const session = await workspaceSessionForCookies("", () => { throw new Error("API must not be called"); });
  assert.equal(session.authenticated, false);
  assert.equal(session.user, null);
  assert.equal(session.csrf_token, "");
  assert.deepEqual(session.workspaces.management_sections, []);
  assert.equal(session.workspaces.manage, false);
  assert.equal(session.workspaces.can_create_books, false);
});

test("requests carrying cookies always verify the real session and propagate API failures", async () => {
  const current = { authenticated: true, user: { id: 1 } };
  assert.equal(await workspaceSessionForCookies("sessionid=opaque", async () => current), current);
  await assert.rejects(() => workspaceSessionForCookies("sessionid=opaque", async () => { throw new Error("unavailable"); }), /unavailable/);
});

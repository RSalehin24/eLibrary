import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { selectedWorkspace, workspaceHome, setWorkspaceView } = await typescriptModule(new URL("../../../app/web/src/lib/workspace-view.ts", import.meta.url));
const admin = { authenticated: true, user: { id: "administrator" }, workspaces: { manage: true } };
const reader = { authenticated: true, user: { id: "reader" }, workspaces: { manage: false } };

test("administrators default to management and can select their own persistent reader view", () => {
  assert.equal(selectedWorkspace(admin), "admin");
  assert.equal(workspaceHome(admin), "/manage/");
  assert.equal(selectedWorkspace(admin, "administrator:reader"), "reader");
  assert.equal(workspaceHome(admin, "administrator:reader"), "/my-books/");
  assert.equal(selectedWorkspace(admin, "another-account:reader"), "admin");
  assert.equal(selectedWorkspace(admin, "invalid"), "admin");
});

test("preferences cannot create management access or skip required authenticator setup", () => {
  assert.equal(selectedWorkspace(reader, "reader:admin"), "reader");
  assert.equal(workspaceHome(reader), "/my-books/");
  assert.equal(selectedWorkspace({ ...admin, authenticated: false }), "reader");
  assert.equal(workspaceHome({ ...admin, user: { ...admin.user, totp_setup_required: true } }), "/profile/");
});

test("the written preference can be read unchanged and uses a secure same-site cookie on HTTPS", () => {
  const oldDocument=globalThis.document, oldLocation=globalThis.location;
  globalThis.document={ cookie:"" }; globalThis.location={ protocol:"https:" };
  try {
    setWorkspaceView(admin.user.id,"reader");
    const value=document.cookie.split(";")[0].split("=")[1];
    assert.equal(selectedWorkspace(admin,value),"reader");
    assert.match(document.cookie,/SameSite=Lax; Secure$/);
  } finally { globalThis.document=oldDocument; globalThis.location=oldLocation; }
});

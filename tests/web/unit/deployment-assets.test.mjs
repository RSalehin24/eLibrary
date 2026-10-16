import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, mkdir, readFile, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const publisher = new URL("../../../deploy/publish-static-assets.mjs", import.meta.url);

async function fixture() {
  const root = await mkdtemp(path.join(tmpdir(), "elibrary-static-test-"));
  const source = path.join(root, "source"), destination = path.join(root, "published");
  await mkdir(source); await mkdir(destination);
  return { source, destination };
}

function publish({ source, destination }) {
  return spawnSync(process.execPath, [publisher.pathname], { env: { ...process.env, STATIC_SOURCE: source, STATIC_DESTINATION: destination }, encoding: "utf8" });
}

test("deployment assets retain old files and safely reuse identical immutable bytes", async () => {
  const files = await fixture();
  await writeFile(path.join(files.source, "new-hash.js"), "new bytes");
  await writeFile(path.join(files.destination, "old-hash.js"), "old bytes");
  assert.equal(publish(files).status, 0);
  assert.equal(publish(files).status, 0);
  assert.equal(await readFile(path.join(files.destination, "old-hash.js"), "utf8"), "old bytes");
  assert.equal(await readFile(path.join(files.destination, "new-hash.js"), "utf8"), "new bytes");
});

test("different bytes under an existing asset name abort without overwriting a live deployment", async () => {
  const files = await fixture();
  await writeFile(path.join(files.source, "same-hash.js"), "new bytes");
  await writeFile(path.join(files.destination, "same-hash.js"), "old bytes");
  assert.notEqual(publish(files).status, 0);
  assert.equal(await readFile(path.join(files.destination, "same-hash.js"), "utf8"), "old bytes");
});

test("destination symlinks cannot become published assets", async () => {
  const files = await fixture();
  await writeFile(path.join(files.source, "asset.js"), "public bytes");
  await symlink(path.join(files.source, "asset.js"), path.join(files.destination, "asset.js"));
  assert.notEqual(publish(files).status, 0);
});

test("source symlinks cannot become published assets", async () => {
  const files = await fixture();
  await writeFile(path.join(files.source, "asset.js"), "public bytes");
  await symlink(path.join(files.source, "asset.js"), path.join(files.source, "linked.js"));
  assert.notEqual(publish(files).status, 0);
});

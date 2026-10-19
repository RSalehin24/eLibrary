import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { archiveEntries, readLocalArchive } = await typescriptModule(new URL("../../../app/web/src/lib/local-epub/archive.ts", import.meta.url));
// Small stored/deflated archives generated with Python's standard zipfile module.
const stored = "UEsDBBQAAAAAAINTU11vYassFAAAABQAAAAIAAAAbWltZXR5cGVhcHBsaWNhdGlvbi9lcHViK3ppcFBLAwQUAAAAAACDU1NdhqYQNgUAAAAFAAAADQAAAGNoYXB0ZXIueGh0bWxoZWxsb1BLAQIUAxQAAAAAAINTU11vYassFAAAABQAAAAIAAAAAAAAAAAAAACAAQAAAABtaW1ldHlwZVBLAQIUAxQAAAAAAINTU12GphA2BQAAAAUAAAANAAAAAAAAAAAAAACAAToAAABjaGFwdGVyLnhodG1sUEsFBgAAAAACAAIAcQAAAGoAAAAAAA==";
const deflated = "UEsDBBQAAAAIAINTU11vYassFgAAABQAAAAIAAAAbWltZXR5cGVLLCjIyUxOLMnMz9NPLShN0q7KLAAAUEsDBBQAAAAIAINTU12GphA2BwAAAAUAAAANAAAAY2hhcHRlci54aHRtbMtIzcnJBwBQSwECFAMUAAAACACDU1Ndb2GrLBYAAAAUAAAACAAAAAAAAAAAAAAAgAEAAAAAbWltZXR5cGVQSwECFAMUAAAACACDU1NdhqYQNgcAAAAFAAAADQAAAAAAAAAAAAAAgAE8AAAAY2hhcHRlci54aHRtbFBLBQYAAAAAAgACAHEAAABuAAAAAAA=";
function bytes(value = stored) { return new Uint8Array(Buffer.from(value, "base64")); }

test("local EPUBs open stored and deflated ZIP content with verified bytes", async () => {
  for (const value of [stored, deflated]) {
    const result = await readLocalArchive(new File([bytes(value)], "book.epub"));
    assert.equal(new TextDecoder().decode(result.get("chapter.xhtml")), "hello");
    assert.equal(result.size, 2);
  }
});

test("corrupted content fails its checksum instead of opening damaged text", async () => {
  const archive = bytes(); archive[101] ^= 1;
  await assert.rejects(() => readLocalArchive(new File([archive], "book.epub")), /invalid_archive/);
});

test("ZIP directories reject encryption, excessive expansion and split archives before decompression", () => {
  for (const mutate of [
    (view, central) => view.setUint16(central + 8, 1, true),
    (view, central) => view.setUint32(central + 24, 9 * 1024 * 1024, true),
    (view, _, end) => view.setUint16(end + 4, 1, true),
    (view, _, end) => view.setUint16(end + 10, 4097, true),
  ]) {
    const archive = bytes(), view = new DataView(archive.buffer), end = archive.length - 22;
    mutate(view, view.getUint32(end + 16, true), end);
    assert.throws(() => archiveEntries(archive.buffer), /invalid_archive/);
  }
});

test("directory and local ZIP names must agree and cannot traverse directories", () => {
  const archive = bytes(); archive[30] = 46;
  assert.throws(() => archiveEntries(archive.buffer), /invalid_archive/);
  for (const input of [new ArrayBuffer(0), new ArrayBuffer(100), bytes().buffer.slice(0, 100)]) assert.throws(() => archiveEntries(input), /invalid_archive/);
});

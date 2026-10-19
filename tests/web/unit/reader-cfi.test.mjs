import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";
const { parseCfi, cfiChapter, matchesCfiText } = await typescriptModule(new URL("../../../app/web/src/lib/reader-cfi-parser.ts", import.meta.url));
const { initialPosition, sessionInitialPosition } = await typescriptModule(new URL("../../../app/web/src/lib/reading-position.ts", import.meta.url));

test("legacy CFI points and ranges preserve structural steps, assertions and UTF-16 offsets", () => {
  const point = parseCfi("epubcfi(/6/4[chapter^,two]!/4[body]/2/1:7)");
  assert.equal(point.spineIndex, 1); assert.equal(point.idref, "chapter,two");
  assert.equal(point.start.offset, 7); assert.equal(point.start.steps[0].assertion, "body");
  const range = parseCfi("epubcfi(/6/2!/4/2,/1:2[before,after;s=b],/1:7)");
  assert.deepEqual(range.start.steps.map(step => step.number), [4, 2, 1]);
  assert.equal(range.start.assertion, "before,after;s=b"); assert.equal(range.end.offset, 7);
});

test("invalid, excessive and nontext CFIs fail without evaluating their contents", () => {
  for (const value of ["", "javascript:alert(1)", "epubcfi(/6/2)", "epubcfi(/6/2!/4/2!/2)", "epubcfi(/6/3!/4/2)", "epubcfi(/06/2!/4/2)", "epubcfi(/6/2!/4/2:Infinity)", "epubcfi(/6/2!/4/2:9007199254740992)", "epubcfi(/6/2!/4/2[unclosed)", `epubcfi(/6/2!/${"2/".repeat(200)}1:0)`, "epubcfi(/6/2!/4/2@0:5)"]) assert.equal(parseCfi(value), null, value);
});

test("text assertions unescape CFI syntax while preserving literal carets and UTF-16 in book text", () => {
  assert.equal(matchesCfiText("🪷 x^y বাংলা", 7, "🪷 x^^y ,বাংলা;s=b"), true);
  assert.equal(matchesCfiText("🪷 x^y বাংলা", 7, "🪷 xy ,বাংলা"), false);
  assert.equal(matchesCfiText("before\n\tবাংলা", 8, "before ,বাংলা"), true);
  assert.equal(matchesCfiText("বাংলা", 99, "বাংলা"), false);
});

test("CFI chapter mapping respects nonlinear spine positions, package structure and item identity", () => {
  const chapters = [{ path: "OPS/a.xhtml", idref: "a", spine_index: 0, spine_step: 6 }, { path: "OPS/b.xhtml", idref: "b", spine_index: 2, spine_step: 6 }];
  assert.equal(cfiChapter("epubcfi(/6/6[b]!/4/2)", chapters), 1);
  for (const value of ["epubcfi(/6/4[b]!/4/2)", "epubcfi(/6/6[a]!/4/2)", "epubcfi(/4/6[b]!/4/2)"]) assert.equal(cfiChapter(value, chapters), -1);
});

test("the original reader's relative paths, fragments and CFI positions open their actual chapter", () => {
  const chapters = [{ path: "OPS/a.xhtml", href: "a.xhtml", label: "A", idref: "a" }, { path: "OPS/b.xhtml", href: "b.xhtml", label: "B", idref: "b" }];
  assert.deepEqual(initialPosition({ last_location: "b.xhtml#section", progress_percent: 0 }, chapters), { chapter: 1, offset: 0, fragment: "#section" });
  const last_location = "epubcfi(/6/4[b]!/4/2/1:12)";
  assert.deepEqual(initialPosition({ last_location, progress_percent: 0 }, chapters), { chapter: 1, offset: 0, legacyCfi: last_location });
  assert.equal(initialPosition({ last_location: "chapter:1:0.4", progress_percent: 0 }, chapters).offset, .4);
});

test("reader sessions from another proven edition use approximate overall progress and report the missing place", () => {
  const session = { chapters: [{ label: "A", path: "a.xhtml" }, { label: "B", path: "b.xhtml" }], reading_progress: { last_location: "chapter:0:0.4", progress_percent: 70 } };
  const fallback = sessionInitialPosition({ ...session, progress_matches_edition: false });
  assert.equal(fallback.chapter, 1);
  assert.ok(Math.abs(fallback.offset - .4) < .0001);
  assert.equal(fallback.restoration, "missing");
  for (const progress_matches_edition of [true, undefined]) {
    assert.deepEqual(sessionInitialPosition({ ...session, progress_matches_edition }), { chapter: 0, offset: .4 });
  }
});

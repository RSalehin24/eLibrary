import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";
const { navigationIsCurrent } = await typescriptModule(new URL("../../../app/web/src/lib/navigation-current.ts", import.meta.url));

test("related reader pages keep Browse or My Books selected", () => {
  for (const path of ["/books/a/", "/contributors/", "/contributors/a/", "/categories/a/", "/series/a/", "/collections/a/"]) assert.equal(navigationIsCurrent(path, "/catalog/"), true);
  assert.equal(navigationIsCurrent("/physical-books/", "/my-books/"), true);
  assert.equal(navigationIsCurrent("/my-books/a/", "/my-books/"), true);
  assert.equal(navigationIsCurrent("/notes/", "/catalog/"), false);
});

test("unfinished sources and manual creation receipts retain the correct admin section", () => {
  assert.equal(navigationIsCurrent("/manage/unfinished/", "/manage/sources/"), true);
  assert.equal(navigationIsCurrent("/manage/book-creations/a/", "/manage/books/"), true);
  assert.equal(navigationIsCurrent("/manage/books/a/", "/manage/"), false);
  assert.equal(navigationIsCurrent("/manage/", "/manage/"), true);
  assert.equal(navigationIsCurrent("/bookshelf/", "/catalog/"), false);
});

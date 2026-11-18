import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(currentFile), "..", "..", "..");

test("home page wires sort controls into the inline catalog toolbar", () => {
  const homePage = fs.readFileSync(
    path.join(repoRoot, "app/frontend/src/pages/HomePage.jsx"),
    "utf8",
  );

  assert.match(
    homePage,
    /const homeSortOptions =\s*homeFilterFields\.find\(\(field\) => field\.key === "sort"\)\?\.options \|\| \[\];/,
  );
  assert.match(homePage, /<CatalogToolbar[\s\S]*sortValue=\{filters\.sort\}/);
  assert.match(homePage, /<CatalogToolbar[\s\S]*sortOptions=\{homeSortOptions\}/);
  assert.match(
    homePage,
    /onSortChange=\{\(nextSort\) => \{[\s\S]*sort: nextSort,[\s\S]*setSearchParams\(cleanQueryParams\(nextFilters\)\);[\s\S]*\}\}/,
  );
  assert.match(homePage, /<BookCardGrid[\s\S]*observeLoadTrigger=\{observeLoadTrigger\}/);
});

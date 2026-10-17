import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { APIError, readJSON } = await typescriptModule(new URL("../../../app/web/src/api/http.ts", import.meta.url));
const { editorialErrorMessage } = await typescriptModule(new URL("../../../app/web/src/lib/editorial-errors.ts", import.meta.url));
const { translateAdmin } = await typescriptModule(new URL("../../../app/web/src/lib/admin-language.ts", import.meta.url));

test("source publication conflicts retain actionable bilingual feedback through the HTTP boundary", async () => {
  for (const detail of [
    "Regenerate the source book to verify its complete text and files.",
    "Finish or resolve the source operation before publication.",
    "Prepare the source book's HTML and EPUB before publication.",
    "Prepare the source book's reader resources before publication.",
  ]) {
    const response = Response.json({ code: "state_conflict", detail }, { status: 409 });
    await assert.rejects(readJSON(response), error => {
      assert.ok(error instanceof APIError);
      assert.equal(error.detail, detail);
      const message = editorialErrorMessage(error);
      assert.doesNotMatch(message, /তথ্য বদলেছে/);
      assert.equal(translateAdmin("bn", message), message);
      assert.notEqual(translateAdmin("en", message), message);
      return true;
    });
  }
});

test("unrecognized server details stay hidden and revision conflicts still request a refresh", () => {
  for (const detail of ["Internal diagnostic", "constructor", "__proto__", ""]) {
    const error = new APIError("Unavailable", 409, { code: "state_conflict", detail });
    assert.equal(editorialErrorMessage(error), "বইটির তথ্য বদলেছে। নতুন তথ্য খুলে তারপর আবার চেষ্টা করুন।");
  }
  assert.match(editorialErrorMessage(new APIError("Bad data", 400)), /চিহ্নিত ঘরগুলোর/);
  assert.match(editorialErrorMessage(new Error("Internal diagnostic")), /অনুরোধটি নিশ্চিত করা যায়নি/);
});

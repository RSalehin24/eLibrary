import assert from "node:assert/strict";
import { test } from "node:test";
import { metadataActorFallback, metadataSourceLabel } from "../../../app/web/src/lib/metadata-history.ts";
import { typescriptModule } from "./typescript-module.mjs";

const { translateAdmin } = await typescriptModule(new URL("../../../app/web/src/lib/admin-language.ts", import.meta.url));

test("metadata provenance has readable labels in both site languages", () => {
  for (const source of ["editorial", "editorial-relationships", "manual", "manual_edit_before", "manual_edit_after", "scrape", "curated", "before_regeneration", "regeneration"]) {
    const label = metadataSourceLabel(source);
    assert.notEqual(label, source);
    assert.equal(translateAdmin("bn", label), label);
    assert.notEqual(translateAdmin("en", label), label);
  }
});

test("unknown history sources use a safe generic label", () => {
  for (const source of ["constructor", "__proto__", "unknown-source"]) {
    assert.equal(metadataSourceLabel(source), "বইয়ের তথ্য সংরক্ষণ");
  }
});

test("missing editor details do not mislabel a human edit as automatic", () => {
  assert.equal(metadataActorFallback("editorial"), "সম্পাদকের তথ্য নেই");
  assert.equal(metadataActorFallback("manual_edit_before"), "সম্পাদকের তথ্য নেই");
  assert.equal(metadataActorFallback("curated"), "স্বয়ংক্রিয়ভাবে সংরক্ষিত");
});

test("metadata history and optional note controls are translated", () => {
  assert.equal(translateAdmin("en", "তথ্যের ইতিহাস"), "Metadata History");
  assert.equal(translateAdmin("en", "পরিবর্তনের কারণ (ঐচ্ছিক)"), "Edit note (optional)");
  assert.equal(translateAdmin("en", "স্বয়ংক্রিয়ভাবে সংরক্ষিত"), "Saved automatically");
});

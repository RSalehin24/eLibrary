import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";
import { test } from "node:test";
import { jobErrorMessage, waitDuration } from "../../../app/web/src/lib/job-errors.ts";
import { catalogStateLabel } from "../../../app/web/src/lib/catalog-state.ts";

const { adminLanguage, translateAdmin } = await typescriptModule(new URL("../../../app/web/src/lib/admin-language.ts", import.meta.url));

test("automation guidance describes automatic checks instead of manual editorial review", () => {
  const messages = [
    "০ রাখলে শুধু উৎসের পরিচিতি সংগ্রহ হবে। প্রস্তুত বই সম্পাদকের পর্যালোচনার অপেক্ষায় থাকবে।",
    "নির্ধারিত সময়ে নতুন উৎস আবিষ্কার করুন এবং নির্বাচিত সীমার মধ্যে বই প্রস্তুত করুন। প্রকাশের আগে সম্পাদকের পর্যালোচনা প্রয়োজন।",
    "তথ্য সম্পাদনার পরে পর্যালোচনা করুন, তারপর প্রকাশ করুন। প্রকাশিত বই সম্পাদনা করলে পর্যালোচনা শেষ হওয়া পর্যন্ত তা জনসাধারণের তালিকা থেকে সরবে।",
  ];
  for (const message of messages) {
    assert.match(translateAdmin("bn", message), /স্বয়ংক্রিয় যাচাই/);
    assert.doesNotMatch(translateAdmin("bn", message), /পর্যালোচনা/);
    assert.match(translateAdmin("en", message), /automatically after successful checks/);
    assert.doesNotMatch(translateAdmin("en", message), /require review|until review/);
  }
});

test("admin language accepts only the supported preference and uses Bengali by default", () => {
  assert.equal(adminLanguage("en"), "en"); assert.equal(adminLanguage("bn"), "bn");
  for (const value of [undefined, "", "fr", "EN", "__proto__"]) assert.equal(adminLanguage(value), "bn");
});

test("admin actions use clear English and Bengali without translating book titles or diagnostic codes", () => {
  assert.equal(translateAdmin("en", "বইয়ের উৎস"), "Create Books");
  assert.equal(translateAdmin("bn", "বইয়ের উৎস"), "বই তৈরি করুন");
  assert.equal(translateAdmin("en", "নির্বাচিত বই তৈরি করুন"), "Create Selected Books");
  assert.equal(translateAdmin("bn", "পাঠকের হিসাব"), "ব্যবহারকারী");
  assert.equal(translateAdmin("en", "  পরিবর্তন সংরক্ষণ করুন "), "  Save Changes ");
  for (const value of ["পথের পাঁচালী", "source_url_not_allowed", "constructor", "__proto__", ""]) assert.equal(translateAdmin("en", value), value);
});

test("book actions do not override the catalog page's existing labels", () => {
  assert.equal(translateAdmin("bn", "বই পরিচালনা"), "বইয়ের তালিকা");
  assert.equal(translateAdmin("en", "বই পরিচালনা"), "Books");
  assert.equal(translateAdmin("en", "বইয়ের কাজ"), "Book Actions");
});

test("waiting time uses useful units at second, minute, hour and day boundaries", () => {
  for (const [seconds, value, label] of [[0, 0, "সেকেন্ড"], [59, 59, "সেকেন্ড"], [60, 1, "মিনিট"], [3599, 59, "মিনিট"], [3600, 1, "ঘণ্টা"], [86400, 1, "দিন"], [209264, 2, "দিন"]]) {
    assert.deepEqual(waitDuration(seconds), { value, label });
  }
});

test("unknown diagnostic codes show a safe readable fallback", () => {
  for (const code of ["unknown_failure", "constructor", "__proto__"]) assert.equal(translateAdmin("en", jobErrorMessage(code)), "The job could not finish. Open its details to inspect the problem.");
});

test("catalog discovery failures and empty results explain the problem in both languages", () => {
  for (const code of ["source_catalog_layout_unrecognized", "source_catalog_empty", "source_catalog_pagination_stalled", "source_catalog_pagination_invalid", "source_discovery_metadata_invalid"]) {
    const message = jobErrorMessage(code);
    assert.notEqual(translateAdmin("en", message), message);
    assert.equal(translateAdmin("bn", message), message);
  }
  assert.equal(translateAdmin("en", "কোনো বই পাওয়া যায়নি"), "No Books Found");
  assert.equal(translateAdmin("en", "বই বেছে নিয়ে তৈরি করুন →"), "Choose Books to Create");
});

test("archived catalog records and revoked permissions have distinct labels", () => {
  assert.equal(translateAdmin("en", catalogStateLabel("archived")), "Archived");
  assert.equal(translateAdmin("en", "প্রত্যাহৃত"), "Revoked");
  assert.equal(catalogStateLabel("unrecognized_state"), "unrecognized_state");
  assert.equal(catalogStateLabel("constructor"), "constructor");
});

test("source verification failures and author controls are translated in both languages", () => {
  for (const code of ["source_export_content_mismatch", "source_verification_missing"]) {
    const message = jobErrorMessage(code);
    assert.notEqual(translateAdmin("en", message), message);
    assert.equal(translateAdmin("bn", message), message);
  }
  assert.equal(translateAdmin("en", "অসম্পূর্ণ বই"), "Unfinished Books");
  assert.equal(translateAdmin("en", "সব ভূমিকা"), "All Roles");
  assert.equal(translateAdmin("en", "বই প্রকাশিত হয়েছে"), "Book Published");
});

test("translated count suffixes retain their spacing and manual review is not requested", () => {
  assert.equal(`12${translateAdmin("en", "টি বই")}`, "12 books");
  assert.equal(`12${translateAdmin("en", "টি পরিচিতি")}`, "12 entries");
  assert.equal(translateAdmin("en", "এই সম্পর্কগুলো বইয়ের অনুমতি নির্ধারণেও ব্যবহৃত হয়। পরিবর্তনের পরে বইটি আবার পর্যালোচনা করুন।"), "Authors and categories also determine book permissions.");
  assert.equal(translateAdmin("bn", "এই সম্পর্কগুলো বইয়ের অনুমতি নির্ধারণেও ব্যবহৃত হয়। পরিবর্তনের পরে বইটি আবার পর্যালোচনা করুন।"), "লেখক ও বিভাগের তথ্য বইয়ের অনুমতি নির্ধারণেও ব্যবহৃত হয়।");
});

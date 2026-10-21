import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { announceSiteLanguage, browserLanguage, subscribeSiteLanguage, translateSite, updateDocumentLanguage } = await typescriptModule(new URL("../../../app/web/src/lib/site-language.ts", import.meta.url));
const { translateFieldError } = await typescriptModule(new URL("../../../app/web/src/lib/field-errors.ts", import.meta.url));
const { jobTimestamp } = await typescriptModule(new URL("../../../app/web/src/lib/job-status.ts", import.meta.url));

test("public, account and reader interfaces translate without changing unsupported text", () => {
  for (const [bn, en] of [["বই খুঁজুন", "Browse Books"], ["অ্যাকাউন্টে প্রবেশ করুন", "Sign In to Your Account"], ["প্রোফাইল ও নিরাপত্তা", "Profile & Security"], ["পড়ার সেটিংস", "Reading Settings"], ["পাঠানো বাতিল করুন", "Cancel Delivery"]]) {
    assert.equal(translateSite("en", bn), en);
    assert.equal(translateSite("bn", bn), bn);
  }
  for (const text of ["পথের পাঁচালী", "source_url_not_allowed", "__proto__", "constructor", ""]) assert.equal(translateSite("en", text), text);
});

test("site translation preserves surrounding whitespace and normalizes authored multiline copy", () => {
  assert.equal(translateSite("en", "  আমার বই "), "  My Books ");
  assert.equal(translateSite("en", "বইয়ের নাম বা\n লেখকের নাম দিয়ে খুঁজুন।"), "Search by book title or author.");
});

test("static and offline pages read the same preference and retain the legacy cookie fallback", () => {
  const previous = globalThis.document;
  try {
    for (const [cookie, expected] of [["", "bn"], ["library-language=en", "en"], ["library-admin-language=en", "en"], ["library-language=bn; library-admin-language=en", "bn"], ["library-language=invalid", "bn"]]) {
      globalThis.document = { cookie }; assert.equal(browserLanguage(), expected);
    }
  } finally { globalThis.document = previous; }
});

test("language changes and focus notify mounted views without retaining removed listeners", () => {
  const previous = globalThis.window;
  try {
    globalThis.window = new EventTarget(); let changes = 0;
    const unsubscribe = subscribeSiteLanguage(() => changes++);
    announceSiteLanguage(); window.dispatchEvent(new Event("focus")); assert.equal(changes, 2);
    unsubscribe(); announceSiteLanguage(); assert.equal(changes, 2);
  } finally { globalThis.window = previous; }
});

test("My Books actions and author browsing use the selected interface language", () => {
  for (const [bn, en] of [["আমার বইয়ে যোগ করুন", "Add to My Books"], ["আমার বই থেকে সরান", "Remove from My Books"], ["আমার বই দেখুন", "View My Books"], ["সব ভূমিকা", "All Roles"], ["লেখক ও সহযোগী", "Authors & Contributors"]]) {
    assert.equal(translateSite("en", bn), en);
    assert.equal(translateSite("bn", bn), bn);
  }
});

test("language changes localize authored page titles and preserve book titles", () => {
  const previous = globalThis.document;
  let authored = "প্রোফাইল ও নিরাপত্তা";
  try {
    globalThis.document = { title: "প্রোফাইল ও নিরাপত্তা | বাংলা পাঠাগার", documentElement: { lang: "bn" }, querySelector: () => ({ getAttribute: () => authored }) };
    updateDocumentLanguage("en");
    assert.equal(document.title, "Profile & Security | Bangla Library"); assert.equal(document.documentElement.lang, "en");
    updateDocumentLanguage("bn"); assert.equal(document.title, "প্রোফাইল ও নিরাপত্তা | বাংলা পাঠাগার");
    authored = ""; document.title = "পথের পাঁচালী | বাংলা পাঠাগার";
    updateDocumentLanguage("en"); assert.equal(document.title, "পথের পাঁচালী | Bangla Library");
  } finally { globalThis.document = previous; }
});

test("field validation translates supported messages and preserves unknown diagnostics", () => {
  assert.equal(translateFieldError("bn", "Current password is incorrect."), "বর্তমান পাসওয়ার্ডটি সঠিক নয়।");
  assert.equal(translateFieldError("en", "Current password is incorrect."), "Current password is incorrect.");
  assert.equal(translateFieldError("bn", "This password is too short. It must contain at least 12 characters."), "অন্তত ১২ অক্ষরের পাসওয়ার্ড দিন।");
  assert.equal(translateFieldError("bn", "Ensure this field has no more than 100 characters."), "সর্বোচ্চ ১০০ অক্ষর লিখুন।");
  assert.equal(translateFieldError("bn", "Ensure this field has at least 12 characters."), "অন্তত ১২ অক্ষর লিখুন।");
  assert.equal(translateFieldError("bn", "The password is too similar to the full name."), "পাসওয়ার্ডের সঙ্গে আপনার ব্যক্তিগত তথ্যের বেশি মিল আছে। অন্য পাসওয়ার্ড দিন।");
  assert.equal(translateFieldError("bn", "Enter a Kindle email ending in @kindle.com."), "@kindle.com দিয়ে শেষ হয় এমন Kindle ইমেইল দিন।");
  for (const language of ["bn", "en"]) assert.equal(translateFieldError(language, "source_response_too_large"), "source_response_too_large");
});

test("dates use a twelve-hour Dhaka clock with localized digits and day periods", () => {
  const value = "2026-10-17T03:18:00Z";
  const bn = jobTimestamp(value, "bn"), en = jobTimestamp(value, "en");
  assert.match(bn, /১৭.*২০২৬/); assert.match(bn, /৯:১৮.*সকাল/); assert.match(bn, /ঢাকা/);
  assert.doesNotMatch(bn, /[A-Za-z0-9]/); assert.match(en, /9:18 AM.*Dhaka/);
  assert.match(jobTimestamp("2026-10-17T18:30:00Z", "en"), /October 18, 2026, 12:30 AM/);
  assert.match(jobTimestamp("2026-10-17T06:00:00Z", "en"), /12:00 PM/);
  assert.match(jobTimestamp("2026-10-17T15:00:00Z", "en"), /9:00 PM/);
  assert.equal(jobTimestamp(null, "bn"), "—");
});

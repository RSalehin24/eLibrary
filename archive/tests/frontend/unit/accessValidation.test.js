import assert from "node:assert/strict";
import test from "node:test";

import {
  formatAccountAccess,
  getAccountAccessLabels,
} from "../../../app/frontend/src/features/access/utils.js";
import {
  getKindleEmailValidationState,
  getEmailValidationState,
  isValidKindleEmail,
  isValidEmail,
  normalizeEmail,
} from "../../../app/frontend/src/utils/email.js";

test("normalizeEmail trims surrounding whitespace before validation", () => {
  assert.equal(normalizeEmail("  reader@example.com  "), "reader@example.com");
});

test("isValidEmail accepts standard addresses and rejects malformed values", () => {
  assert.equal(isValidEmail("reader@example.com"), true);
  assert.equal(isValidEmail("reader"), false);
  assert.equal(isValidEmail(" reader@example.com "), true);
});

test("getEmailValidationState reports the normalized value and validity", () => {
  assert.deepEqual(getEmailValidationState(" reader@example.com "), {
    normalizedEmail: "reader@example.com",
    hasEmailInput: true,
    emailLooksValid: true,
  });
  assert.deepEqual(getEmailValidationState("invalid-address"), {
    normalizedEmail: "invalid-address",
    hasEmailInput: true,
    emailLooksValid: false,
  });
});

test("isValidKindleEmail accepts Kindle domains and rejects other addresses", () => {
  assert.equal(isValidKindleEmail("reader@kindle.com"), true);
  assert.equal(isValidKindleEmail(" reader@kindle.com "), true);
  assert.equal(isValidKindleEmail("reader@free.kindle.com"), false);
  assert.equal(isValidKindleEmail("reader@example.com"), false);
  assert.equal(isValidKindleEmail("reader"), false);
});

test("getKindleEmailValidationState layers Kindle-only checks on top of email validation", () => {
  assert.deepEqual(getKindleEmailValidationState(" reader@kindle.com "), {
    normalizedEmail: "reader@kindle.com",
    hasEmailInput: true,
    emailLooksValid: true,
    baseEmailLooksValid: true,
    kindleDomainLooksValid: true,
  });
  assert.deepEqual(getKindleEmailValidationState("reader@example.com"), {
    normalizedEmail: "reader@example.com",
    hasEmailInput: true,
    emailLooksValid: false,
    baseEmailLooksValid: true,
    kindleDomainLooksValid: false,
  });
  assert.deepEqual(getKindleEmailValidationState("reader"), {
    normalizedEmail: "reader",
    hasEmailInput: true,
    emailLooksValid: false,
    baseEmailLooksValid: false,
    kindleDomainLooksValid: false,
  });
});

test("getAccountAccessLabels maps scope labels and keeps them sorted", () => {
  const scopeLabelMap = new Map([
    ["read:durable", "Read durable books"],
    ["metadata:edit", "Edit metadata"],
  ]);

  assert.deepEqual(
    getAccountAccessLabels(
      {
        global_scopes: ["read:durable", "metadata:edit"],
      },
      scopeLabelMap,
    ),
    ["Edit metadata", "Read durable books"],
  );
});

test("formatAccountAccess joins mapped permission labels for filtering", () => {
  const scopeLabelMap = new Map([["read:durable", "Read durable books"]]);

  assert.equal(
    formatAccountAccess(
      {
        global_scopes: ["read:durable"],
      },
      scopeLabelMap,
    ),
    "Read durable books",
  );
  assert.equal(formatAccountAccess({ global_scopes: [] }, scopeLabelMap), "-");
});

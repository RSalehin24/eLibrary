import assert from "node:assert/strict";
import test from "node:test";

import {
  firstPayloadIssue,
  payloadFieldMessage,
  payloadMessage,
} from "../../../app/frontend/src/api/text.js";
import { formatApiError } from "../../../app/frontend/src/features/access/utils.js";

test("payloadMessage prefers direct detail strings", () => {
  assert.equal(
    payloadMessage({ detail: "Reset token is invalid or expired." }),
    "Reset token is invalid or expired.",
  );
});

test("payloadMessage extracts the first field validation message", () => {
  assert.equal(
    payloadMessage({
      new_password: ["Ensure this field has at least 12 characters."],
    }),
    "Ensure this field has at least 12 characters.",
  );
});

test("payloadMessage falls through empty detail values to nested field errors", () => {
  assert.equal(
    payloadMessage({
      detail: "",
      entries: [{ content: ["At least one submission value is required."] }],
    }),
    "At least one submission value is required.",
  );
});

test("firstPayloadIssue keeps the field key for labeled notifications", () => {
  assert.deepEqual(
    firstPayloadIssue({
      password: ["Ensure this field has at least 12 characters."],
    }),
    {
      field: "password",
      message: "Ensure this field has at least 12 characters.",
    },
  );
});

test("payloadFieldMessage applies a provided label map", () => {
  assert.equal(
    payloadFieldMessage(
      { global_scopes: ["Select at least one account permission."] },
      { global_scopes: "Account permissions" },
    ),
    "Account permissions: Select at least one account permission.",
  );
});

test("formatApiError humanizes unmapped field names", () => {
  assert.equal(
    formatApiError({
      message: "Request failed.",
      payload: {
        new_password: ["Ensure this field has at least 12 characters."],
      },
    }),
    "New Password: Ensure this field has at least 12 characters.",
  );
});

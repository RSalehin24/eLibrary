import assert from "node:assert/strict";
import test from "node:test";

import { createApiError } from "../../../app/frontend/src/api/errors.js";

test("createApiError preserves backend detail messages for 502 responses", () => {
  const error = createApiError({
    status: 502,
    path: "/access/books/example/send-to-kindle/",
    payload: {
      detail:
        "Kindle delivery could not authenticate with Brevo SMTP.",
    },
  });

  assert.equal(
    error.message,
    "Kindle delivery could not authenticate with Brevo SMTP.",
  );
  assert.equal(error.status, 502);
});

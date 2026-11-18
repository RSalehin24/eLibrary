import assert from "node:assert/strict";
import test from "node:test";

import { parseResponse } from "../../../app/frontend/src/api/response.js";

test("parseResponse treats no-content responses as successful empty payloads", async () => {
  const response = new Response(null, {
    status: 204,
    headers: {
      "content-type": "application/json",
    },
  });

  assert.equal(await parseResponse(response), null);
});

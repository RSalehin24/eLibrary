import { createRequire } from "node:module";

const require = createRequire(
  new URL("../../../../app/frontend/package.json", import.meta.url),
);

export const { expect, test } = require("playwright/test");

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(currentFile), "..", "..", "..");

test("local docker stack passes CELERY_TASK_ALWAYS_EAGER into app containers", () => {
  const composeFile = fs.readFileSync(
    path.join(repoRoot, "local/compose/docker-compose.yml"),
    "utf8",
  );

  assert.match(
    composeFile,
    /CELERY_TASK_ALWAYS_EAGER:\s*\$\{CELERY_TASK_ALWAYS_EAGER:-0\}/,
  );
});

test("local env example documents CELERY_TASK_ALWAYS_EAGER", () => {
  const envExample = fs.readFileSync(
    path.join(repoRoot, "local/env/app.env.example"),
    "utf8",
  );

  assert.match(envExample, /^CELERY_TASK_ALWAYS_EAGER=0$/m);
});

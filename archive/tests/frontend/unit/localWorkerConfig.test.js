import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(currentFile), "..", "..", "..");

test("local docker worker pins single-task ingestion processing", () => {
  const composeFile = fs.readFileSync(
    path.join(repoRoot, "local/compose/docker-compose.yml"),
    "utf8",
  );

  assert.match(
    composeFile,
    /CELERY_WORKER_CONCURRENCY:\s*1/,
  );
  assert.match(
    composeFile,
    /CELERY_WORKER_PREFETCH_MULTIPLIER:\s*1/,
  );
  assert.match(
    composeFile,
    /CELERY_WORKER_MAX_TASKS_PER_CHILD:\s*1/,
  );
  assert.match(
    composeFile,
    /--pool=solo/,
  );
  assert.match(
    composeFile,
    /--concurrency=1/,
  );
  assert.match(
    composeFile,
    /--prefetch-multiplier=1/,
  );
  assert.match(
    composeFile,
    /--max-tasks-per-child=1/,
  );
});

test("local env example documents the safer worker defaults", () => {
  const envExample = fs.readFileSync(
    path.join(repoRoot, "local/env/app.env.example"),
    "utf8",
  );

  assert.match(envExample, /^CELERY_WORKER_CONCURRENCY=1$/m);
  assert.match(envExample, /^CELERY_WORKER_PREFETCH_MULTIPLIER=1$/m);
  assert.match(envExample, /^CELERY_WORKER_MAX_TASKS_PER_CHILD=1$/m);
});

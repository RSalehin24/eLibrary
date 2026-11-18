import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(currentDir, "../../../../");
const localEnvPath = path.join(repoRoot, "local/env/.env");

let cachedEnv = null;

function parseEnvFile(rawValue) {
  const parsed = {};
  for (const line of rawValue.split(/\r?\n/)) {
    if (!line || line.trim().startsWith("#") || !line.includes("=")) {
      continue;
    }
    const separatorIndex = line.indexOf("=");
    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    if (key) {
      parsed[key] = value;
    }
  }
  return parsed;
}

export function loadLocalEnv() {
  if (!cachedEnv) {
    const fileEnv = fs.existsSync(localEnvPath)
      ? parseEnvFile(fs.readFileSync(localEnvPath, "utf8"))
      : {};
    cachedEnv = { ...fileEnv, ...process.env };
  }
  return cachedEnv;
}

export function getRepoRoot() {
  return repoRoot;
}

export function getSuperAdminCredentials() {
  const env = loadLocalEnv();
  return {
    email: env.SUPER_ADMIN_EMAIL || "admin@example.com",
    password: env.SUPER_ADMIN_PASSWORD || "changeme",
  };
}

export function getLiveBaseUrls() {
  const env = loadLocalEnv();
  const frontendPort = env.FRONTEND_PORT || "5173";
  const backendPort = env.BACKEND_PORT || "8000";
  return {
    frontend: process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${frontendPort}`,
    backend: process.env.PLAYWRIGHT_BACKEND_URL || `http://127.0.0.1:${backendPort}`,
  };
}

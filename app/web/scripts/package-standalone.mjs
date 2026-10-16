import { cp, stat } from "node:fs/promises";
import { buildServiceWorker } from "./build-service-worker.mjs";

const applicationRoot = new URL("../", import.meta.url);
await cp(new URL(".next/static/", applicationRoot), new URL(".next/standalone/.next/static/", applicationRoot), { recursive: true });

const publicDirectory = new URL("public/", applicationRoot);
let publicMetadata;
try {
  publicMetadata = await stat(publicDirectory);
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}
if (publicMetadata) await cp(publicDirectory, new URL(".next/standalone/public/", applicationRoot), { recursive: true });
await buildServiceWorker(applicationRoot);

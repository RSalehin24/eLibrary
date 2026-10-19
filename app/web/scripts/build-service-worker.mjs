import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";

export async function buildServiceWorker(applicationRoot) {
  const staticDirectory = new URL(".next/static/", applicationRoot);
  const assets = (await readdir(staticDirectory, { recursive: true })).filter((path) => /\.(?:js|css|woff2)$/.test(path)).sort().map((path) => `/_next/static/${path}`);
  const offline = await readFile(new URL("src/pwa/offline.html", applicationRoot));
  const localReader = await readFile(new URL(".next/server/app/local-reader.html", applicationRoot));
  const worker = await readFile(new URL("src/pwa/service-worker.mjs", applicationRoot), "utf8");
  const buildIdentifier = await readFile(new URL(".next/BUILD_ID", applicationRoot), "utf8");
  const version = createHash("sha256").update(buildIdentifier).update(worker).update(offline).update(localReader).update(JSON.stringify(assets)).digest("hex").slice(0, 20);
  const offlinePath = `/offline.${createHash("sha256").update(offline).digest("hex").slice(0, 20)}.html`;
  const localReaderPath = `/local-reader-shell.${createHash("sha256").update(localReader).digest("hex").slice(0, 20)}.html`;
  const publicDirectory = new URL(".next/standalone/public/", applicationRoot);
  await mkdir(publicDirectory, { recursive: true });
  await writeFile(new URL(offlinePath.slice(1), publicDirectory), offline);
  await writeFile(new URL(localReaderPath.slice(1), publicDirectory), localReader);
  const configuration = { cache: `library-static-${version}`, assets: [...assets, offlinePath, localReaderPath], offline: offlinePath, localReader: localReaderPath };
  await writeFile(new URL("sw.js", publicDirectory), `${worker}\nconfigureWorker(self, ${JSON.stringify(configuration)});\n`);
}

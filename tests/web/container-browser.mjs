import { createServer, request } from "node:http";
import { spawn } from "node:child_process";

function localForwarder(port) {
  return createServer((incoming, outgoing) => {
  const upstream = request(new URL(incoming.url, `http://host.docker.internal:${port}`), {
    method: incoming.method, headers: { ...incoming.headers, host: `127.0.0.1:${port}` },
  }, (response) => { outgoing.writeHead(response.statusCode, response.headers); response.pipe(outgoing); });
  upstream.on("error", () => { outgoing.writeHead(502); outgoing.end("Local test server is unavailable."); });
  incoming.pipe(upstream);
  });
}

const ports = [Number(new URL(process.env.FOUNDATION_WEB_URL ?? "http://127.0.0.1:3000").port), Number(new URL(process.env.FOUNDATION_READER_API_URL ?? "http://127.0.0.1:8000").port)];
const servers = ports.map(localForwarder);
await Promise.all(servers.map((server, index) => new Promise((resolve, reject) => { server.once("error", reject); server.listen(ports[index], "127.0.0.1", resolve); })));
const runner = spawn("node", ["app/web/node_modules/playwright/cli.js", "test", "--config", "tests/web/playwright.config.mjs", ...process.argv.slice(2)], { stdio: "inherit" });
runner.once("exit", (code) => { for (const server of servers) { server.closeAllConnections(); server.close(); } process.exitCode = code ?? 1; });

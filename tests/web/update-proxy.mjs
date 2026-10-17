import { createServer, request } from "node:http";
import { readFile } from "node:fs/promises";

export class UpdateProxy {
  revision = 1;
  offline = false;
  failProgress = false;
  origin = "http://127.0.0.1:5174";

  async start() {
    const worker = await readFile(new URL("../../app/web/.next/standalone/public/sw.js", import.meta.url), "utf8");
    this.server = createServer((incoming, outgoing) => {
      if (this.offline) { incoming.socket.destroy(); return; }
      if (this.failProgress && incoming.method === "PUT" && /^\/api\/v1\/reading\/sessions\/[0-9a-f-]+\/progress\/$/.test(incoming.url)) {
        outgoing.writeHead(503, { "Content-Type": "application/json" }); outgoing.end('{"code":"unavailable"}'); return;
      }
      if (incoming.url === "/sw.js") {
        outgoing.writeHead(200, { "Content-Type": "text/javascript", "Cache-Control": "no-store", "Service-Worker-Allowed": "/" });
        outgoing.end(worker.replace(/library-static-[0-9a-f]{20}/, `library-static-test-update-${this.revision}`));
        return;
      }
      const target = new URL(process.env.FOUNDATION_WEB_URL ?? "http://127.0.0.1:3000");
      const upstream = request(new URL(incoming.url, target), { method: incoming.method, headers: { ...incoming.headers, host: target.host } }, (response) => {
        const headers = { ...response.headers };
        if (headers["content-security-policy"]) headers["content-security-policy"] = headers["content-security-policy"].replaceAll(target.origin, this.origin);
        outgoing.writeHead(response.statusCode, headers); response.pipe(outgoing);
      });
      upstream.on("error", () => { outgoing.writeHead(502); outgoing.end("Test upstream unavailable."); });
      incoming.pipe(upstream);
    });
    await new Promise((resolve, reject) => { this.server.once("error", reject); this.server.listen(5174, "127.0.0.1", resolve); });
  }

  async stop() {
    this.server.closeAllConnections();
    await new Promise((resolve, reject) => this.server.close((error) => error ? reject(error) : resolve()));
  }
}

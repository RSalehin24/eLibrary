import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import { createReadStream, statSync } from 'node:fs';
import { IncomingMessage, ServerResponse, createServer } from 'node:http';
import { extname, join, normalize, sep } from 'node:path';

const browserRoot = join(import.meta.dirname, '../browser');
// why: the only caller is Caddy on the internal network; trust just the two headers the public URL needs.
const angularApp = new AngularNodeAppEngine({
  trustProxyHeaders: ['x-forwarded-host', 'x-forwarded-proto'],
});
const CONTENT_TYPES: Record<string, string> = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
};
const DEFAULT_PORT = 4000;
const FIXTURE_BOOK = {
  slug: 'bangla-bhasha',
  title: 'বাংলা ভাষা',
  author: 'নমুনা লেখক',
  description: 'বাংলা ভাষার ইতিহাস ও বিকাশ নিয়ে একটি নমুনা বই।',
  subjects: ['ভাষা', 'ইতিহাস'],
};

/** Resolves a URL path inside the browser build; `undefined` for anything outside it or `index.html`. */
function staticFile(urlPath: string): string | undefined {
  const candidate = normalize(join(browserRoot, decodeURIComponent(urlPath)));
  if (!candidate.startsWith(browserRoot + sep) || candidate.endsWith(`${sep}index.html`)) {
    return undefined;
  }
  return statSync(candidate, { throwIfNoEntry: false })?.isFile() ? candidate : undefined;
}

function sendJson(res: ServerResponse, body: unknown): void {
  res.setHeader('content-type', 'application/json');
  res.end(JSON.stringify(body));
}

function handle(req: IncomingMessage, res: ServerResponse, next: (error?: unknown) => void): void {
  const path = new URL(req.url ?? '/', 'http://localhost').pathname;
  if (path === '/internal/health') {
    res.end('ok');
    return;
  }
  // Spike stand-in for the gateway: the real data comes from /api/catalog through Caddy and the gateway.
  if (path === `/api/catalog/books/${FIXTURE_BOOK.slug}`) {
    sendJson(res, FIXTURE_BOOK);
    return;
  }
  const file = staticFile(path);
  if (file !== undefined) {
    res.setHeader('content-type', CONTENT_TYPES[extname(file)] ?? 'application/octet-stream');
    res.setHeader('cache-control', 'public, max-age=31536000, immutable');
    createReadStream(file).pipe(res);
    return;
  }
  render(req, res, next).catch(next);
}

async function render(
  req: IncomingMessage,
  res: ServerResponse,
  next: (error?: unknown) => void,
): Promise<void> {
  const response = await angularApp.handle(req);
  if (response) {
    await writeResponseToNodeResponse(response, res);
    return;
  }
  next();
}

function notFound(res: ServerResponse): void {
  res.statusCode = 404;
  res.end('not found');
}

if (isMainModule(import.meta.url) || process.env['pm_id']) {
  const server = createServer((req, res) => {
    handle(req, res, () => {
      notFound(res);
    });
  });
  server.listen(Number(process.env['PORT'] ?? DEFAULT_PORT), '0.0.0.0');
  // PID 1 in a container ignores SIGTERM unless handled (S-06): drain and exit.
  process.on('SIGTERM', () => {
    server.close(() => {
      process.exit(0);
    });
  });
}

/** Request handler used by the Angular CLI (dev server and build). */
export const reqHandler = createNodeRequestHandler(handle);

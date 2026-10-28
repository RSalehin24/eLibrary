# Independent reader, resources, local files, and offline behavior

Tasks R01/R04. Use [service ownership](../../shared/contracts/service-boundaries.md) and [data/state rules](../../shared/contracts/data-and-state.md).

## R01: extraction sequence

1. Build the planned `app/reader` with approved React/TypeScript/Next.js tooling. Move reader UI/helpers behind focused renderer/navigation/settings/persistence interfaces; inject library and local document/persistence adapters. Share behavior only where both modes actually use it. Do not add a generic plugin architecture.
2. Keep library reading/session/progress/annotations on the existing `/api/v1/reading/` endpoints. Include same-origin credentials and CSRF for mutations. Use server-returned resource bases, never constructed filesystem paths or bearer URLs.
3. Own `/reader/`, `/reader/[identifier]/`, `/local-reader/` documents and `/reader-assets/` build assets. Configure the build/proxy so framework hydration/route requests also reach the reader without colliding with website assets. Produce and test the complete route/asset manifest before switching the proxy.
4. Full document links cross the service boundary; disable cross-service router prefetch. Sanitize return destinations and preserve language/current permitted theme. Reader launch cannot accidentally create a second read-once opening.
5. Add reader-specific lint/unit/type/build/start scripts by reusing actual repository tooling, document their real commands, and validate the independently started artifact. Do not merely leave scripts that run the website build.
6. Add internal liveness/readiness and release identity as defined in the service contract. A missing reader build fails reader readiness while website catalog/account routes keep working. Switch all reader-owned routes atomically after integration passes.

**R01 checks:** clean standalone build/start with website UI stopped; shared API/session still available; direct/reloaded deep link; failed/missing session; CSRF denial; unauthorized resource UUID; logout in another tab; role navigation; language; hash/history; iframe/font/image/media assets; browser runtime requests all in the intended namespace. Test root proxy precedence and no HTML fallback returned as JavaScript or chapter content.

Opening uses the session's exact prepared build and verified spine order, preserving cover/title/front matter/body order rather than prepending duplicate generated pages. Loading, invalid EPUB, unavailable file, expired access and retry each have distinct feedback. Initial failure cannot display a Prepared/Reading success state or save a default position. A missing cover uses the ordinary title/credits fallback; a missing required body/resource prevents readiness.

Rollback a failed route switch by restoring the last matching proxy/reader build pair. Do not serve mismatched assets or change API ownership to repair routing. Keep tests pointed at an immutable completed build.

## R04: EPUB trust boundary

Library preparation currently lives in `app/backend/apps/access/reading/{epub_archive,epub_paths,preparation,document_safety}.py`. Retain account/expiry checks for every protected resource and single-range media behavior. Parent-owned event binding and the WebKit observation workaround remain constrained by authored-script and network-isolation tests.

| Surface | Required behavior and regression |
| --- | --- |
| Archive | Reject traversal/absolute/encoded-escape/backslash/NUL/duplicate paths, encrypted/special files, malformed ZIP/XML, unexpected compression, oversized expansion and undeclared resources. Validate before extracting. |
| Authored content | Scripts, event handlers, executable URLs, forms, remote CSS/imports and authenticated network escape are blocked. Do not solve a renderer/event bug by allowing authored execution. |
| Internal links | Resolve package-relative/fragment links only to manifest resources; exact footnote/backlink and chapter navigation preserve state. Broken links give usable feedback. |
| External links | Require an explicit user gesture, validate schemes, and open safe external destinations without opener authority. They must not navigate an authenticated iframe into the application. |
| Images/tables/poetry | Preserve meaningful structure and reading order; overflow contained within content, missing-resource feedback, responsive images, correct line/stanza breaks, no reading-position jump after delayed image load. |
| Audio/video | No autoplay; keyboard/touch controls, ranged protected fetch, safe seek, time/spatial positions where supported, and pause/cleanup on chapter close. Expired permissions stop further loads. |
| XML/package | No external entity fetching; validate manifest, spine, contents targets/media types and resource paths. Invalid books fail preparation before being called ready. |

Use current numeric limits, do not silently unify them: protected backend EPUB is at most 128 MiB compressed, 256 MiB expanded, 32 MiB per resource, 10,000 resources, 100:1 ratio, and 2 MiB XML. Browser local EPUB is at most 24 MiB compressed, 64 MiB expanded, 8 MiB per entry, and 4,096 entries. Website upload remains its existing 24 MiB intake limit. Shared library/local presentation does not imply identical memory capacity. Check actual streamed/decompressed bytes, not only supplied headers.

## Device-local behavior

Local reader accepts a user-selected `.epub` into browser memory, validates MIME/package/CRC/size/paths, and renders with the same command registry and layout. It never submits file names, hashes, text, resources, selections, or local progress to website/engine/telemetry. A library API request must not be triggered by opening or searching a local file.

Persist non-content appearance/shortcut settings using the existing guarded browser-storage mechanism. Local file bytes, resources and reading position stay in memory; after a reload the user selects the file again and starts a new local session. The inspected local reader has no durable bookmark/annotation/progress store, so this plan retains that boundary. Do not add file storage or account sync to meet offline acceptance. Library-only bookmark/annotation/Kindle/server-save actions are absent or disabled with a clear reason in local mode; the registry must not pretend they succeeded. Local search, contents, typography, views and navigation remain available.

On replacing/closing a file or leaving the reader, abort outstanding parsing/search/load work, detach listeners/observers, pause media, revoke created object URLs, release byte buffers and reset previous file state. A slow result from file A cannot overwrite opened file B. Corrupt/unsupported/encrypted/over-limit files retain a useful file-selection retry path without application crashes.

## One offline worker and coordinated update

Website owns one root worker/install manifest. Reader build emits an anonymous public local-reader shell and a fingerprinted asset manifest; the website worker packaging consumes this artifact without importing website account HTML. Reader build does not depend on a website build, and website can package a previously released compatible reader artifact.

| Request | Offline/cache policy |
| --- | --- |
| Public reader shell/fingerprinted assets | Precache from the signed-off build manifest, credentials omitted; immutable checksum collision is an error. |
| `/local-reader/` navigation with no network | Serve only the anonymous local-file shell. File selection continues entirely on device. |
| Other document navigation with no network | Generic offline notice with retry; never cached authenticated HTML. |
| HTTP 4xx/5xx document response | Preserve actual status/error; no fake offline success document. |
| API, chapter iframe, media, mutation, reader session | Network only/no-store; no generic HTML fallback for resource requests. |

Retain the existing two prior public cache generations and matching static assets for open clients; do not clear unrelated origin caches. This short public-asset retention is necessary runtime compatibility, unrelated to disposable historical book data. Website and reader release manifests declare their compatible shell/asset fingerprints.

Waiting updates are explicit user actions. Before reload, check dirty drafts and pending mutations, capture/flush actual progress, then recheck for changes made while flushing. A failed save or progress conflict blocks update and retains a visible retry/resolution path. Only the accepting tab reloads. Other tabs keep their matching resources. Do not build or mutate generated worker artifacts during PWA acceptance.

**R04 evidence:** use `tests/web/e2e/{reader-media,local-reader,pwa}.spec.mjs`, reader unit tests, backend preparation/media tests, actual service-worker cache inspection, offline proxy interruption and malicious EPUB fixtures. Test blocked storage, unsupported fullscreen/decompression capabilities, cancel/open-file race, local network silence, authored script/network escape, old open tab during an update, and latest progress before reload in all supported simulator profiles.

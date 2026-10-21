# Local EPUB reader

`/local-reader/` opens a file from the device without an account or upload.
The former `/epub-reader` and `/epub-reader/index.html` addresses redirect here.
The reader shares library-reader typography, themes, scroll/page/spread views,
contents controls, keyboard and touch navigation, and immersive mode.

Files and generated resource URLs stay in memory. Closing the book or leaving
the page releases them. Reading preferences can persist in browser storage;
local book contents, positions and annotations are not saved to the account.
Select the file again after reloading. Library books and account features still
require the network and normal authorization.

## Offline launch

The production build renders a public, anonymous reader shell without requiring
the API. The service worker precaches its fingerprinted HTML and static assets
with credentials omitted. After the worker is installed, a failed navigation to
`/local-reader/` can use that shell. Other pages retain the generic offline
notice. Authenticated pages, API responses and library books never enter this
cache. Development mode does not register a production worker.

## Format and isolation

Supported EPUBs use ordinary stored or deflated ZIP entries, UTF-8 XML/HTML,
an OPF spine and optional EPUB 3 navigation or NCX contents. Limits are 24 MiB
compressed, 64 MiB expanded, 8 MiB per entry, 4,096 archive entries and 2,000
reading-order/contents entries. Invalid sizes, checksums, paths, duplicate
archive names and unsupported compression fail explicitly. Encrypted archives,
DRM and packages with an encryption manifest are rejected.

Chapter documents render in a sandbox with the same-origin/script flags needed
for parent-installed reader handlers in WebKit. Sanitization removes active
elements, event handlers and external resources; a first-in-head content security
policy explicitly blocks authored scripts, external requests and forms.
Images, fonts, styles, declared audio/video and WebVTT captions resolve to the
selected archive's local resources. Media uses native controls and metadata
preload; authored autoplay is removed. Posters and sources use archive blob URLs.
Unavailable external media is removed while retaining fallback text. The CSP
allows only local media blobs; no network media request is permitted. Playback
still depends on the browser's supported codecs.
Internal chapter links use the reader's navigation. External links are disabled.
No third-party reader or archive dependency is installed.

## Regression evidence

`tests/web/unit/local-epub-archive.test.mjs` checks stored/deflated entries,
checksums, truncation, names and archive limits. Service-worker tests verify the
public-shell cache boundary. `tests/web/e2e/local-reader.spec.mjs` covers file
selection, malformed-file recovery, chapter links, an embedded image, typography,
views, immersive controls, script/network blocking and actual offline loading.
Its fourth journey opens an actual embedded WAV offline, verifies that it stays
paused, seeks with native media controls and checks that external media is blocked.
Current browser results belong in the implementation handoff; do not infer
physical-device or every-EPUB compatibility from these fixtures.

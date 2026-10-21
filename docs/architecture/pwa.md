# Installation, offline launch, and updates

The standalone build supplies one root `/manifest.webmanifest` and `/sw.js`.
The Bengali manifest has a stable `/` identity, root scope/start URL,
standalone display, 192/512 PNG icons, a maskable icon, phone/desktop screenshots,
and Discover/My Books shortcuts. Icons are rendered from repository-native
vector artwork at build time. Installation screenshots show the actual public
workspace and contain no account information.

The Install action appears when Chrome supplies its installation event and
invokes the prompt only after a click. Dismissal is remembered in local storage.
Installed standalone windows hide the action. Help includes Chrome-menu
instructions when a prompt is unavailable. iPhone help explains Safari's Share,
Add to Home Screen, and optional Open as Web App controls, following
[Apple's instructions](https://support.apple.com/guide/iphone/open-as-web-app-iphea86e5236/27/ios/27).
HTTPS is required in production;
local loopback is used for development verification. See
[Next.js PWA support](https://nextjs.org/docs/app/guides/progressive-web-apps) and
[installation events](https://developer.mozilla.org/en-US/docs/Web/API/BeforeInstallPromptEvent).

## Cache boundary

`postbuild` generates the worker from the exact production static-file list,
build identifier, worker policy, and offline-document checksum. It precaches
only fingerprinted Next.js scripts/styles/fonts, a generic offline document and
the public local-file reader shell, with credentials omitted. API responses, authenticated HTML,
book resources, navigation payloads, reader identifiers, and mutations are
excluded. Top-level document navigation uses the network; network failure shows
the generic notice; `/local-reader/` instead uses its anonymous public shell.
Real HTTP errors retain their status and body. Iframe
navigation bypasses the offline fallback, so an unavailable chapter cannot be
mistaken for completed reading progress.

Each deployment gets a versioned cache. Activation keeps two previous library
caches and leaves unrelated caches alone. The deployment must retain previous
fingerprinted assets for existing open sessions. The static publisher retains
old files, reuses identical bytes, and rejects conflicting immutable filenames;
unit and isolated deployment checks cover this behavior. Service-worker scripts use
`no-store`, root scope, and `updateViaCache: none`. The development server does
not register a production worker. See
[service-worker lifecycle](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers).

## Update behavior

A waiting worker displays an explicit update action. It does not force a reload
while someone is reading or editing. Acceptance first checks unsaved edits and
pending mutations, then flushes the reader's latest progress. It checks again
for edits made while saving. Failed progress saves block reload. Only the tab
that accepted the update reloads; other open tabs remain running. A worker can
also activate on a later launch after its previous clients close. See
[PWA update guidance](https://web.dev/learn/pwa/update).

## Verification and limits

Initial PWA acceptance recorded 21 worker/coordinator/account/job/password-link/reader
helper tests. All 108 Chromium, 108 WebKit, and 108 Linux Firefox journeys passed against the
standalone build. The selected Android/Pixel 7 and iPhone 13 browser profiles each passed
30 discovery, library, reading, account, and PWA journeys. Installation-help
checks are included in all five final browser profiles after the Safari copy update. Browser
checks cover manifest/icon dimensions, offline launch without private cached
responses, a synthetic install-event dismissal, real waiting-worker updates
with unsaved editorial work, unchanged second tabs, and progress saving before
reader reload, blocked preference storage without an uncaught error, and guarded
updates during profile editing, unfinished authenticator setup, Kindle recipient
selection, account/grant editing, and password-link editing.
Update/network-interruption tests use a local HTTP fixture proxy
and the actual production worker; generated files are not edited. The proxy
also disconnects upstream requests because browser offline emulation does not
consistently interrupt service-worker fetches. General network-injection tests
block workers; reader/PWA specs explicitly allow and verify the real worker.

The user's subsequent simulator-only request added accepted-install, standalone
relaunch, and reinstall-after-removal journeys. Twelve focused installation
checks passed across Chromium, Pixel 7, and iPhone 13 profiles. The helper
simulates native installation events/display mode while retaining actual app UI
and worker behavior; physical OS installation is outside that scope. See
[simulator acceptance](../operations/simulator-acceptance.md).
Firefox runs with the matching Linux Playwright bundle because this host cannot
launch its macOS bundle; see [verification tooling](verification-tooling.md).
Library books require a network connection. Device-local EPUB files can open
offline after the public reader shell has been installed; contents remain in
memory and never enter the worker cache. See
[local EPUB reader](../operations/local-epub-reader.md) for limits and isolation.
Its three local-file journeys passed Chromium, WebKit, Android and iPhone browser
profiles and pinned Linux Firefox. Current combined checks and their revisions
are recorded in the implementation handoff; the earlier PWA counts above are
historical evidence for that acceptance scope.

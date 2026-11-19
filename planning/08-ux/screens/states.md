# Error, empty, forbidden, offline and not-found states

Status: DRAFT

**Purpose**: every screen renders from `PageState<T> = Loading | Empty | Ready | Failed | Forbidden | NotFound | Offline` with an exhaustive match (REQ-WEB-001). This spec fixes how each non-Ready state looks and reads on every screen. States are rendered in place; there is no `/403`, `/500` or `/offline` route ([route map](../route-map.md)). **Service owner**: web. **Requirements**: REQ-WEB-001, 002, 003, 004, 020.

## 401 versus 403 (REQ-WEB-002)

| Response | UI |
|---|---|
| 401 `unauthenticated` | clear session state, go to `/sign-in?next=<current route>`, return after sign-in; no error toast |
| 403 `forbidden` | Forbidden state in place with the reason below; session stays; no redirect |
| 403 `mfa_required` | go to the TOTP step |
| 403 `csrf_invalid` | refresh the session response and retry once, silently |
| 404 | NotFound state |
| 409 `stale_revision`, `invalid_transition`, `conflict` | inline message with the current server state and a Refresh action |
| 422 / `validation_failed` | field errors |
| 429 / 503 / 504 | Failed state with the typed message and automatic retry with backoff for reads; form state kept; no polling, no forced reload |
| network loss | Offline state |

There is never a "the application restarted" message.

## Variants

| State | Look and copy | Actions |
|---|---|---|
| Loading | skeleton sized to the final content; spinner only for a button; no layout shift | none |
| Empty | one line saying why it is empty and what to do next; no illustration; neutral tone | one primary action when there is one |
| Failed | tonal error banner (error colour used only here) with the typed message from the catalog keyed by error code, and the correlation id in small text for support | Retry |
| Forbidden | neutral surface (not error red): "You do not have access to this" plus the reason from the denial (`no grant`, `read-once used`, `not published`, `account not active`, `needs two-step verification`) and the way forward (ask an administrator, sign in) | Back, Sign in |
| NotFound | "This page was not found" with a link to Library; used for unknown routes, deleted or unpublished books | Go to Library |
| Offline | persistent banner "No connection, showing what is already loaded"; mutations disabled with a reason; reconnect retries with backoff and keeps form state | Retry now |
| SSR failure | public pages fall back to the client shell with a typed error page | Retry |

A route or action the capability set hides is also refused by the guard (`CanMatch`); the guard shows Forbidden for a signed-in user and starts the 401 path for a visitor.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.state.loading` | Loading | লোড হচ্ছে |
| `ux.state.retry` | Try again | আবার চেষ্টা করুন |
| `ux.state.forbidden.title` | You do not have access to this | এটি দেখার অনুমতি আপনার নেই |
| `ux.state.forbidden.ask` | Ask an administrator to grant access. | অনুমতির জন্য অ্যাডমিনকে বলুন। |
| `ux.state.notfound.title` | This page was not found | পৃষ্ঠাটি পাওয়া যায়নি |
| `ux.state.notfound.home` | Go to Library | লাইব্রেরিতে যান |
| `ux.state.offline` | No connection. Showing what is already loaded. | সংযোগ নেই। আগে লোড হওয়া অংশ দেখানো হচ্ছে। |
| `ux.state.failed` | Something went wrong. Please try again. | কিছু ভুল হয়েছে। আবার চেষ্টা করুন। |
| `ux.state.session.expired` | Please sign in again to continue. | চালিয়ে যেতে আবার সাইন ইন করুন। |

Analytics: none. Accessibility: a state change is announced in a polite live region (assertive only for blocking errors); the heading receives focus after a route-level state; errors never rely on colour alone.

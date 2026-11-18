import { manifestFromLaunchUrl } from "./params.js";

function identity(value) {
  return value;
}

export function resolveReaderManifestUrl(payload, normalizeUrl = identity) {
  const manifestUrl =
    payload?.manifest_url || manifestFromLaunchUrl(payload?.launch_url || "");

  return normalizeUrl(manifestUrl);
}

export function normalizeReaderManifestPayload(
  manifest,
  normalizeUrl = identity,
) {
  if (!manifest || typeof manifest !== "object") {
    return manifest;
  }

  const nextManifest = { ...manifest };
  [
    "manifest_url",
    "epub_download_url",
    "html_preview_url",
    "reading_session_url",
    "bookmarks_url",
    "highlights_url",
  ].forEach((field) => {
    if (typeof nextManifest[field] === "string" && nextManifest[field]) {
      nextManifest[field] = normalizeUrl(nextManifest[field]);
    }
  });

  return nextManifest;
}

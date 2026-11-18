import { API_BASE_URL } from "./constants.js";
import { normalizeAppUrl } from "./urlNormalization.js";

export function resolveAppUrl(url) {
  if (!url || typeof window === "undefined") {
    return url;
  }

  return normalizeAppUrl(url, {
    currentOrigin: window.location.origin,
    apiBaseUrl: API_BASE_URL,
  });
}

export function resolveApiUrl(url) {
  if (!url || typeof window === "undefined") {
    return url;
  }

  const apiBasePath = API_BASE_URL.replace(/\/$/, "");

  let normalizedPath = String(url);
  try {
    const resolved = new URL(normalizedPath, window.location.origin);
    const resolvedPath = resolved.pathname;
    if (
      resolvedPath === apiBasePath ||
      resolvedPath.startsWith(`${apiBasePath}/`)
    ) {
      normalizedPath = resolved.toString();
    } else {
      normalizedPath = `${apiBasePath}/${normalizedPath.replace(/^\/+/, "")}`;
    }
  } catch {
    normalizedPath = `${apiBasePath}/${normalizedPath.replace(/^\/+/, "")}`;
  }

  return normalizeAppUrl(normalizedPath, {
    currentOrigin: window.location.origin,
    apiBaseUrl: API_BASE_URL,
  });
}

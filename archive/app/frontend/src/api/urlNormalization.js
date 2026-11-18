export function normalizeAppUrl(
  url,
  { currentOrigin = "", apiBaseUrl = "/api" } = {},
) {
  if (!url || !currentOrigin) {
    return url;
  }

  try {
    const apiBasePath = new URL(apiBaseUrl, currentOrigin).pathname.replace(
      /\/$/,
      "",
    );
    const resolved = new URL(url, currentOrigin);
    const manifestUrl = resolved.searchParams.get("manifest");

    if (
      resolved.pathname === apiBasePath ||
      resolved.pathname.startsWith(`${apiBasePath}/`)
    ) {
      return `${currentOrigin}${resolved.pathname}${resolved.search}${resolved.hash}`;
    }

    if (manifestUrl) {
      const normalizedManifestUrl = normalizeAppUrl(manifestUrl, {
        currentOrigin,
        apiBaseUrl,
      });
      if (
        normalizedManifestUrl &&
        normalizedManifestUrl !== manifestUrl
      ) {
        resolved.searchParams.set("manifest", normalizedManifestUrl);
      }
    }

    return resolved.toString();
  } catch {
    return url;
  }
}

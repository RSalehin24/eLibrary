export function decodeValue(value) {
  if (!value) {
    return "";
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function manifestFromLaunchUrl(launchUrlValue) {
  if (!launchUrlValue) {
    return "";
  }

  try {
    const baseOrigin =
      typeof window !== "undefined" ? window.location.origin : "http://localhost";
    const parsed = new URL(launchUrlValue, baseOrigin);
    const manifest = parsed.searchParams.get("manifest") || "";
    return manifest ? decodeValue(manifest) : "";
  } catch {
    return "";
  }
}

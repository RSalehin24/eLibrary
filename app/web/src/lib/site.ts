export const siteName = "বাংলা পাঠাগার";

export function siteOrigin() {
  const origin = process.env.PUBLIC_SITE_URL ?? "http://127.0.0.1:3000";
  const url = new URL(origin);
  if (process.env.NODE_ENV === "production" && url.protocol !== "https:") {
    throw new Error("PUBLIC_SITE_URL must use HTTPS in production.");
  }
  return url.origin;
}

export function canonicalURL(path: string) {
  return new URL(path, siteOrigin()).toString();
}

export function bengaliNumber(value: number) {
  return new Intl.NumberFormat("bn").format(value);
}

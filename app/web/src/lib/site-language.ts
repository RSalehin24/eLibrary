import { adminMessages, type AdminLanguage } from "./admin-language";
import { siteEnglishMessages } from "./site-messages";
import { adminLanguage } from "./admin-language";
import { siteName } from "./site";

export function updateDocumentLanguage(language: AdminLanguage) {
  const authored = document.querySelector('meta[name="library:ui-title"]')?.getAttribute("content");
  const parts = document.title.split(" | ");
  const brand = translateSite(language, siteName);
  if (parts.length > 1) document.title = `${authored ? translateSite(language, authored) : parts.slice(0, -1).join(" | ")} | ${brand}`;
  else if (authored || parts[0] === siteName || parts[0] === translateSite("en", siteName)) document.title = authored ? translateSite(language, authored) : brand;
  document.documentElement.lang = language;
}

export function browserLanguage() {
  const stored = document.cookie.split(";").map((cookie) => cookie.trim()).find((cookie) => cookie.startsWith("library-language="));
  return adminLanguage(stored?.slice("library-language=".length));
}

export function translateSite(language: AdminLanguage, text: string): string {
  if (language === "bn") return text;
  const key = text.trim().replace(/\s+/g, " ");
  const translated = Object.hasOwn(siteEnglishMessages, key) ? siteEnglishMessages[key] : Object.hasOwn(adminMessages, key) ? adminMessages[key].en : undefined;
  return translated !== undefined ? text.replace(text.trim(), translated) : text;
}

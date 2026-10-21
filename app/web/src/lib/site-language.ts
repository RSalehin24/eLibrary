import { adminMessages, type AdminLanguage } from "./admin-language";
import { siteEnglishMessages } from "./site-messages";
import { adminLanguage } from "./admin-language";
import { siteName } from "./site";

export function updateDocumentLanguage(language: AdminLanguage) {
  const authored = document.querySelector('meta[name="library:ui-title"]')?.getAttribute("content");
  const parts = document.title.split(" | ");
  const brand = translateSite(language, siteName);
  let title = document.title;
  if (parts.length > 1) title = `${authored ? translateSite(language, authored) : parts.slice(0, -1).join(" | ")} | ${brand}`;
  else if (authored || parts[0] === siteName || parts[0] === translateSite("en", siteName)) title = authored ? translateSite(language, authored) : brand;
  if (document.title !== title) document.title = title;
  document.documentElement.lang = language;
}

export function browserLanguage() {
  const cookies = document.cookie.split(";").map(cookie => cookie.trim());
  const stored = cookies.find(cookie => cookie.startsWith("library-language=")) ?? cookies.find(cookie => cookie.startsWith("library-admin-language="));
  return adminLanguage(stored?.split("=")[1]);
}

export function subscribeSiteLanguage(notify: () => void) {
  window.addEventListener("library-language-change", notify);
  window.addEventListener("focus", notify);
  return () => { window.removeEventListener("library-language-change", notify); window.removeEventListener("focus", notify); };
}

export function announceSiteLanguage() { window.dispatchEvent(new Event("library-language-change")); }

export function translateSite(language: AdminLanguage, text: string): string {
  if (language === "bn") return text;
  const key = text.trim().replace(/\s+/g, " ");
  const translated = Object.hasOwn(siteEnglishMessages, key) ? siteEnglishMessages[key] : Object.hasOwn(adminMessages, key) ? adminMessages[key].en : undefined;
  return translated !== undefined ? text.replace(text.trim(), translated) : text;
}

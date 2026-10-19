export type LocalItem = { id: string; path: string; type: string; properties: string[] };
export type LocalContents = { label: string; chapter_index: number | null; fragment: string; depth: number };
export type LocalPackage = { title: string; chapters: LocalItem[]; items: LocalItem[]; navigation: LocalContents[] };
const root = "https://epub.invalid/";

export function localPath(href: string, base = "") {
  try {
    const url = new URL(href, root + base);
    if (url.origin !== new URL(root).origin || url.username || url.password) return null;
    const path = decodeURIComponent(url.pathname.slice(1));
    return /[\\\u0000]/.test(path) ? null : { path, fragment: decodeURIComponent(url.hash.slice(1)) };
  } catch { return null; }
}

export function xmlDocument(value: string) {
  if (/<!DOCTYPE|<!ENTITY/i.test(value)) throw new Error("invalid_epub");
  const document = new DOMParser().parseFromString(value, "application/xml");
  if (document.querySelector("parsererror")) throw new Error("invalid_epub");
  return document;
}

export function archiveText(files: Map<string, Uint8Array>, path: string) {
  const value = files.get(path);
  if (!value) throw new Error("invalid_epub");
  return new TextDecoder("utf-8", { fatal: true }).decode(value);
}

function navigation(files: Map<string, Uint8Array>, items: LocalItem[], chapters: LocalItem[]) {
  const item = items.find(entry => entry.properties.includes("nav")) ?? items.find(entry => entry.type === "application/x-dtbncx+xml");
  if (!item) return [];
  const document = xmlDocument(archiveText(files, item.path));
  const contents: LocalContents[] = [];
  const nodes = item.type === "application/x-dtbncx+xml" ? Array.from(document.getElementsByTagName("navPoint")) : Array.from(document.querySelector('nav[*|type="toc"],nav[role="doc-toc"]')?.querySelectorAll("li") ?? document.querySelectorAll("nav li"));
  for (const node of nodes) {
    if (contents.length >= 2000) throw new Error("invalid_epub");
    const anchor = item.type === "application/x-dtbncx+xml" ? node.querySelector(":scope > content") : node.querySelector(":scope > a");
    const target = localPath(anchor?.getAttribute("href") ?? anchor?.getAttribute("src") ?? "", item.path);
    const label = node.querySelector(":scope > navLabel,:scope > a,:scope > span")?.textContent?.trim().slice(0, 500) ?? "";
    let depth = 0, parent = node.parentElement;
    while (parent) { if (["li", "navPoint"].includes(parent.localName)) depth += 1; parent = parent.parentElement; }
    const index = chapters.findIndex(chapter => chapter.path === target?.path);
    if (label) contents.push({ label, chapter_index: index < 0 ? null : index, fragment: target?.fragment ?? "", depth });
  }
  return contents;
}

export function readLocalPackage(files: Map<string, Uint8Array>): LocalPackage {
  if (files.has("META-INF/encryption.xml")) throw new Error("encrypted_epub");
  const container = xmlDocument(archiveText(files, "META-INF/container.xml"));
  const path = localPath(container.querySelector("rootfile")?.getAttribute("full-path") ?? "")?.path;
  if (!path) throw new Error("invalid_epub");
  const document = xmlDocument(archiveText(files, path));
  const items = Array.from(document.querySelectorAll("manifest > item")).map(element => {
    const resolved = localPath(element.getAttribute("href") ?? "", path);
    if (!resolved || !files.has(resolved.path)) throw new Error("invalid_epub");
    return { id: element.getAttribute("id") ?? "", path: resolved.path, type: element.getAttribute("media-type") ?? "", properties: (element.getAttribute("properties") ?? "").split(/\s+/) };
  });
  const chapters = Array.from(document.querySelectorAll("spine > itemref")).filter(element => element.getAttribute("linear") !== "no").map(element => {
    const item = items.find(item => item.id === element.getAttribute("idref"));
    if (!item || !["application/xhtml+xml", "text/html"].includes(item.type)) throw new Error("invalid_epub");
    return item;
  });
  if (!chapters.length || chapters.length > 2000) throw new Error("invalid_epub");
  return { title: document.querySelector("metadata > title,metadata > *|title")?.textContent?.trim().slice(0, 500) || "EPUB", chapters, items, navigation: navigation(files, items, chapters) };
}

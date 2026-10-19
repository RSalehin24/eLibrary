export type BookmarkTextPosition = { chapter: number; offset: number; quote: string };
const PREFIX = "text:";

export function bookmarkPositionAtOffset(text: string, chapter: number, offset: number): BookmarkTextPosition {
  const following = text.slice(offset);
  const skipped = following.length - following.trimStart().length;
  return { chapter, offset: offset + skipped, quote: Array.from(following.trimStart()).slice(0, 32).join("").trimEnd() };
}

export function bookmarkTextLocation(position: BookmarkTextPosition) {
  const location = PREFIX + JSON.stringify(position);
  return location.length <= 255 && parseBookmarkTextLocation(location) ? location : null;
}

export function parseBookmarkTextLocation(location: string): BookmarkTextPosition | null {
  if (!location.startsWith(PREFIX) || location.length > 255) return null;
  let value: unknown;
  try { value = JSON.parse(location.slice(PREFIX.length)); }
  catch { return null; }
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const anchor = value as Record<string, unknown>;
  if (Object.keys(anchor).sort().join(",") !== "chapter,offset,quote") return null;
  if (!Number.isInteger(anchor.chapter) || Number(anchor.chapter) < 0 || Number(anchor.chapter) > 9999) return null;
  if (!Number.isInteger(anchor.offset) || Number(anchor.offset) < 0 || Number(anchor.offset) > 32_000_000) return null;
  if (typeof anchor.quote !== "string" || !anchor.quote.trim() || Array.from(anchor.quote).length > 32) return null;
  return { chapter: Number(anchor.chapter), offset: Number(anchor.offset), quote: anchor.quote };
}

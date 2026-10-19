import { visibleAnchor } from "./reader-document";
import { selectorFromRange, selectionRange, textNodes } from "./reader-text";
import { bookmarkTextLocation, bookmarkPositionAtOffset, type BookmarkTextPosition } from "./bookmark-text-position";

export function captureBookmarkText(document: Document, chapter: number) {
  const anchor = visibleAnchor(document);
  if (!anchor) return null;
  const range = document.createRange();
  range.setStart(anchor.node, anchor.offset); range.collapse(true);
  const offset = selectorFromRange(document, range).start;
  const text = textNodes(document.body).map(node => node.textContent ?? "").join("");
  const position = bookmarkPositionAtOffset(text, chapter, offset);
  const location = bookmarkTextLocation(position);
  return location ? { location, preview_text: position.quote } : null;
}

export function bookmarkTextRange(document: Document, anchor: BookmarkTextPosition) {
  const range = selectionRange(document, { start: anchor.offset, end: anchor.offset + anchor.quote.length });
  if (!range || range.toString() !== anchor.quote) return null;
  range.collapse(true);
  return range;
}

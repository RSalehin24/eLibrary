import { isPaged } from "./reader-document";

export function readerPageState(document: Document) {
  const root = document.scrollingElement ?? document.documentElement;
  const size = isPaged(document) ? root.clientWidth : root.clientHeight;
  const extent = isPaged(document) ? root.scrollWidth : root.scrollHeight;
  const offset = isPaged(document) ? root.scrollLeft : root.scrollTop;
  return { current: Math.round(offset / Math.max(size, 1)) + 1, total: Math.max(1, Math.ceil(extent / Math.max(size, 1))) };
}

export function turnReaderPage(document: Document, direction: number) {
  const root = document.scrollingElement ?? document.documentElement;
  const paged = isPaged(document);
  const maximum = paged ? root.scrollWidth - root.clientWidth : root.scrollHeight - root.clientHeight;
  const offset = paged ? root.scrollLeft : root.scrollTop;
  if (direction < 0 ? offset <= 1 : offset >= maximum - 1) return false;
  if (paged) root.scrollLeft = Math.max(0, Math.min(maximum, (Math.round(offset / root.clientWidth) + direction) * root.clientWidth));
  else root.scrollTop = Math.max(0, Math.min(maximum, offset + direction * root.clientHeight * 0.9));
  return true;
}

export function readerKeyboardDirection(event: KeyboardEvent) {
  if (event.altKey || event.ctrlKey || event.metaKey || event.defaultPrevented) return 0;
  if (event.shiftKey && event.key !== " ") return 0;
  if ((event.target as Element | null)?.closest?.('input,textarea,select,button,a,[contenteditable="true"]')) return 0;
  if (["ArrowLeft", "PageUp"].includes(event.key) || event.key === " " && event.shiftKey) return -1;
  if (["ArrowRight", "PageDown", " "].includes(event.key)) return 1;
  return 0;
}

import { applyAppearance, restoreAnchor, scrollFraction, visibleAnchor, type ReaderAppearance, type ReadingAnchor } from "./reader-document";
import { documentLink } from "./reader-links";
import type { ReadingPosition } from "./reading-position";
import { selectionRange, jumpToRange } from "./reader-annotations";
import { cfiRange } from "./reader-cfi";
import { bookmarkTextRange } from "./bookmark-text-anchor";
import { observeReaderDocument } from "./reader-observation";
import { bindReaderInteraction } from "./reader-interaction";
import type { ReaderGesture } from "./reader-gestures";

export type FrameLocation = { fraction: number; anchor: ReadingAnchor | null };
export type FrameBindings = { src: string; appearance: ReaderAppearance; position: ReadingPosition;
  onPosition: (position: ReadingPosition) => void; onNavigate: (target: URL) => boolean;
  onExternal: (href: string) => void; onFailure: () => void; onRestoreFailure: () => void; onReady: () => void; onDocument: (document: Document) => void; onPage: (direction: number) => void; onShortcut: (event: KeyboardEvent) => void; onGesture: (gesture: ReaderGesture) => void };

export function bindReaderFrame(frame: HTMLIFrameElement, bindings: FrameBindings, location: FrameLocation) {
  const document = frame.contentDocument;
  if (document?.URL === "about:blank") return;
  if (!document?.body || !["text/html", "application/xhtml+xml"].includes(document.contentType)) { bindings.onFailure(); return; }
  if (new URL(document.URL).pathname !== new URL(bindings.src, window.location.origin).pathname) {
    if (!bindings.onNavigate(new URL(document.URL))) bindings.onFailure();
    return;
  }
  if (!location.anchor && (document.scrollingElement?.scrollTop ?? 0) > 0) location.anchor = visibleAnchor(document);
  applyAppearance(document, bindings.appearance);
  const fragmentRestored = !location.anchor && jumpToFragment(document, bindings.position.fragment);
  if (location.anchor || !fragmentRestored) restoreAnchor(document, location.anchor, location.fraction);
  if (bindings.position.fragment && !location.anchor && !fragmentRestored) bindings.onRestoreFailure();
  if (bindings.position.selection && !location.anchor) {
    const range = selectionRange(document, bindings.position.selection);
    const matchingText = !bindings.position.selectionText || range?.toString().trim() === bindings.position.selectionText.trim();
    if (!range || !matchingText || !jumpToRange(document, range)) bindings.onRestoreFailure();
  }
  if (bindings.position.textAnchor && !location.anchor) {
    const range = bookmarkTextRange(document, bindings.position.textAnchor);
    if (!range || !jumpToRange(document, range)) bindings.onRestoreFailure();
  }
  if (bindings.position.legacyCfi && !location.anchor) {
    const range = cfiRange(document, bindings.position.legacyCfi);
    const matchingText = !bindings.position.legacyText || range?.toString().trim() === bindings.position.legacyText.trim();
    if (!range || !matchingText || !jumpToRange(document, range)) bindings.onRestoreFailure();
  }
  let width = frame.clientWidth;
  let height = frame.clientHeight;
  const scroll = () => {
    if (frame.clientWidth === width && frame.clientHeight === height) recordLocation(document, bindings, location);
  };
  const link = (event: MouseEvent) => followDocumentLink(document, bindings, event);
  document.addEventListener("scroll", scroll, { passive: true });
  document.addEventListener("click", link);
  const stopInteraction = bindReaderInteraction(document, bindings.onPage, { shortcut: bindings.onShortcut, gesture: bindings.onGesture });
  const stopObserving = observeReaderDocument(document, () => {
    if (Math.abs(scrollFraction(document) - location.fraction) > 0.0001) scroll();
  });
  const observer = new ResizeObserver(() => {
    applyAppearance(document, bindings.appearance);
    restoreAnchor(document, location.anchor, location.fraction);
    width = frame.clientWidth; height = frame.clientHeight;
  });
  observer.observe(frame);
  scroll();
  bindings.onReady();
  bindings.onDocument(document);
  return () => { stopInteraction(); stopObserving(); document.removeEventListener("scroll", scroll); document.removeEventListener("click", link); observer.disconnect(); };
}

function recordLocation(document: Document, bindings: FrameBindings, location: FrameLocation) {
  location.fraction = scrollFraction(document);
  // Reflow may reveal earlier text on a page; retain the passage being adjusted.
  if (!window.document.querySelector("dialog[open]")) location.anchor = visibleAnchor(document);
  bindings.onPosition({ chapter: bindings.position.chapter, offset: location.fraction });
}

function followDocumentLink(document: Document, bindings: FrameBindings, event: MouseEvent) {
  const anchor = documentLink(event);
  if (!anchor) return;
  event.preventDefault();
  const target = new URL(anchor.href);
  if (target.pathname === new URL(bindings.src, window.location.origin).pathname && jumpToFragment(document, target.hash)) return;
  if (!bindings.onNavigate(target) && ["https:", "http:"].includes(target.protocol)) bindings.onExternal(target.href);
}

function jumpToFragment(document: Document, fragment?: string) {
  if (!fragment) return false;
  let identifier: string;
  try { identifier = decodeURIComponent(fragment.replace(/^#/, "")); }
  catch { return false; }
  const target = document.getElementById(identifier);
  if (!target) return false;
  target.scrollIntoView();
  return true;
}

import { applyAppearance, restoreAnchor, scrollFraction, visibleAnchor, type ReaderAppearance, type ReadingAnchor } from "./reader-document";
import { documentLink } from "./reader-links";
import type { ReadingPosition } from "./reading-position";
import { jumpToSelection } from "./reader-annotations";
import { observeReaderDocument } from "./reader-observation";

export type FrameLocation = { fraction: number; anchor: ReadingAnchor | null };
export type FrameBindings = { src: string; appearance: ReaderAppearance; position: ReadingPosition;
  onPosition: (position: ReadingPosition) => void; onNavigate: (target: URL) => boolean;
  onExternal: (href: string) => void; onFailure: () => void; onReady: () => void; onDocument: (document: Document) => void };

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
  if (location.anchor || !jumpToFragment(document, bindings.position.fragment)) restoreAnchor(document, location.anchor, location.fraction);
  if (bindings.position.selection && !location.anchor) jumpToSelection(document, bindings.position.selection);
  let width = frame.clientWidth;
  let height = frame.clientHeight;
  const scroll = () => {
    if (frame.clientWidth === width && frame.clientHeight === height) recordLocation(document, bindings, location);
  };
  const link = (event: MouseEvent) => followDocumentLink(document, bindings, event);
  document.addEventListener("scroll", scroll, { passive: true });
  document.addEventListener("click", link);
  const stopObserving = observeReaderDocument(document, () => {
    if (Math.abs(scrollFraction(document) - location.fraction) > 0.0001) scroll();
  });
  const observer = new ResizeObserver(() => {
    restoreAnchor(document, location.anchor, location.fraction);
    width = frame.clientWidth; height = frame.clientHeight;
  });
  observer.observe(frame);
  scroll();
  bindings.onReady();
  bindings.onDocument(document);
  return () => { stopObserving(); document.removeEventListener("scroll", scroll); document.removeEventListener("click", link); observer.disconnect(); };
}

function recordLocation(document: Document, bindings: FrameBindings, location: FrameLocation) {
  location.fraction = scrollFraction(document);
  location.anchor = visibleAnchor(document);
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

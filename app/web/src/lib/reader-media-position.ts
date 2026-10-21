import { cfiMediaTarget, cfiRange } from "./reader-cfi";
import { jumpToRange } from "./reader-annotations";
import { isPaged, readingAnchorPoint, type ReadingAnchor } from "./reader-document";
import { mediaSpatialPoint } from "./reader-media-geometry";

const METADATA_WAIT_MS = 10_000;
const METADATA_POLL_MS = 100;
const SEEK_TOLERANCE_SECONDS = .05;
type Restoration = { text?: string; onFailure: () => void; onComplete?: (anchor?: ReadingAnchor) => void };

export function jumpToMedia(element: Element, spatial?: { x: number; y: number }) {
  const document = element.ownerDocument, rectangle = element.getBoundingClientRect();
  if (!rectangle.width && !rectangle.height) return false;
  const point = spatial ? mediaSpatialPoint(element, spatial) : { x: rectangle.left, y: rectangle.top };
  if (!point) return false;
  const root = document.scrollingElement ?? document.documentElement;
  if (isPaged(document)) root.scrollLeft = Math.floor((root.scrollLeft + point.x) / root.clientWidth) * root.clientWidth;
  else root.scrollTop += point.y - root.clientHeight / 3;
  return true;
}

function mediaAnchor(target: NonNullable<ReturnType<typeof cfiMediaTarget>>) {
  const anchor: ReadingAnchor = { node: target.element, offset: 0, top: 0, spatial: target.spatial };
  const point = readingAnchorPoint(anchor);
  return point ? { ...anchor, top: point.y, viewportFraction: point.y / target.element.ownerDocument.documentElement.clientHeight } : undefined;
}

function restoreTimedMedia(target: NonNullable<ReturnType<typeof cfiMediaTarget>>, restoration: Restoration) {
  const element = target.element as HTMLMediaElement;
  element.pause(); element.autoplay = false;
  const started = performance.now();
  let requested = false;
  const fail = () => { restoration.onFailure(); restoration.onComplete?.(); return true; };
  const seek = () => {
    if (!element.isConnected) return true;
    if (element.error || performance.now() - started >= METADATA_WAIT_MS) return fail();
    if (element.readyState < 1) return false;
    if (!Number.isFinite(element.duration) || target.temporal! > element.duration) return fail();
    if (!requested) {
      try { element.currentTime = target.temporal!; requested = true; }
      catch { return fail(); }
    }
    if (element.seeking || element.readyState < 2) return false;
    if (Math.abs(element.currentTime - target.temporal!) > SEEK_TOLERANCE_SECONDS) return fail();
    jumpToMedia(element, target.spatial);
    restoration.onComplete?.(mediaAnchor(target));
    return true;
  };
  if (seek()) return () => {};
  // Parent-owned polling also works in WebKit's script-disabled book document.
  const timer = window.setInterval(() => { if (seek()) window.clearInterval(timer); }, METADATA_POLL_MS);
  return () => window.clearInterval(timer);
}

export function restoreLegacyCfi(document: Document, value: string, restoration: Restoration) {
  const target = cfiMediaTarget(document, value);
  if (target) {
    if (target.temporal !== undefined) (target.element as HTMLMediaElement).controls = true;
    if (restoration.text || !jumpToMedia(target.element, target.spatial)) { restoration.onFailure(); restoration.onComplete?.(); return () => {}; }
    if (target.temporal !== undefined) return restoreTimedMedia(target, restoration);
    restoration.onComplete?.(mediaAnchor(target));
    return () => {};
  }
  const range = cfiRange(document, value);
  const matchingText = !restoration.text || range?.toString().trim() === restoration.text.trim();
  if (!range || !matchingText || !jumpToRange(document, range)) restoration.onFailure();
  restoration.onComplete?.();
  return () => {};
}

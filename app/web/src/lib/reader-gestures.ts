export type ReaderGesture = { kind: "immersive" | "theme" } | { kind: "text"; steps: number };
type Point = { x: number; y: number };
const point = (touch: Touch): Point => ({ x: touch.clientX, y: touch.clientY });
const distance = (first: Point, second: Point) => Math.hypot(first.x - second.x, first.y - second.y);
const interactive = (target: EventTarget | null) => !!(target as Element | null)?.closest?.("a,button,input,select,textarea,summary,[contenteditable],[role=button],[role=link],[role=textbox],audio,video");

export function bindReaderGestures(document: Document, actions: { turn: (direction: number) => void; onGesture: (gesture: ReaderGesture) => void }) {
  let start: Point | null = null, started = 0, travel = 0, lastTap: (Point & { time: number }) | null = null;
  let multi: { distance: number; center: Point; travel: number; pinch: number; resized: boolean } | null = null;
  let blocked = false, lastTouch = 0;
  const clear = () => { start = null; multi = null; blocked = false; travel = 0; };
  const selected = () => document.getSelection()?.isCollapsed === false;
  const onStart = (event: TouchEvent) => {
    if (!event.touches.length) { clear(); return; }
    if (event.touches.length > 2) { blocked = true; return; }
    blocked ||= interactive(event.target) || selected();
    started = event.timeStamp;
    if (event.touches.length === 2) {
      const first = point(event.touches[0]), second = point(event.touches[1]);
      multi = { distance: distance(first, second), center: { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 }, travel: 0, pinch: 0, resized: false };
      lastTap = null; return;
    }
    if (!multi) start = point(event.touches[0]);
  };
  const onMove = (event: TouchEvent) => {
    if (blocked || selected()) return;
    if (!multi || event.touches.length !== 2) { if (start && event.touches[0]) travel = Math.max(travel, distance(start, point(event.touches[0]))); return; }
    const first = point(event.touches[0]), second = point(event.touches[1]);
    multi.travel = Math.max(multi.travel, distance(multi.center, { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 }));
    const current = distance(first, second), delta = current - multi.distance;
    multi.pinch = Math.max(multi.pinch, Math.abs(delta));
    if (Math.abs(delta) < 24) return;
    if (event.cancelable) event.preventDefault();
    actions.onGesture({ kind: "text", steps: Math.trunc(delta / 24) });
    multi.distance = current; multi.resized = true;
  };
  const finishSingle = (event: TouchEvent) => {
    if (!start || !event.changedTouches[0]) return;
    const duration = event.timeStamp - started;
    const end = point(event.changedTouches[0]);
    const horizontal = end.x - start.x, vertical = end.y - start.y;
    if (duration <= 600 && Math.abs(horizontal) > 60 && Math.abs(horizontal) > Math.abs(vertical) * 2) { lastTap = null; actions.turn(horizontal < 0 ? 1 : -1); return; }
    if (duration > 260 || Math.max(travel, distance(start, end)) > 12) { lastTap = null; return; }
    const paired = lastTap && event.timeStamp - lastTap.time <= 300 && distance(lastTap, end) <= 24;
    lastTap = paired ? null : { ...end, time: event.timeStamp };
    if (!paired) return;
    if (event.cancelable) event.preventDefault();
    actions.onGesture({ kind: "immersive" });
  };
  const onEnd = (event: TouchEvent) => {
    lastTouch = event.timeStamp;
    if (event.touches.length > 0) return;
    if (blocked || selected() || interactive(event.target)) { lastTap = null; clear(); return; }
    if (multi && !multi.resized && event.timeStamp - started <= 260 && multi.travel <= 24 && multi.pinch <= 18) actions.onGesture({ kind: "theme" });
    if (!multi) finishSingle(event);
    clear();
  };
  const doubleClick = (event: MouseEvent) => { if (event.timeStamp - lastTouch > 400 && !interactive(event.target) && !selected()) actions.onGesture({ kind: "immersive" }); };
  const cancel = () => { clear(); lastTap = null; };
  document.addEventListener("touchstart", onStart, { passive: true });
  document.addEventListener("touchmove", onMove, { passive: false });
  document.addEventListener("touchend", onEnd, { passive: false });
  document.addEventListener("touchcancel", cancel);
  document.addEventListener("dblclick", doubleClick);
  return () => { document.removeEventListener("touchstart", onStart); document.removeEventListener("touchmove", onMove); document.removeEventListener("touchend", onEnd); document.removeEventListener("touchcancel", cancel); document.removeEventListener("dblclick", doubleClick); };
}

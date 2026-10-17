import { isPaged } from "./reader-document";
import { readerKeyboardDirection } from "./reader-pagination";
import { bindReaderGestures, type ReaderGesture } from "./reader-gestures";
export function bindReaderInteraction(document: Document, turn: (direction: number) => void, actions: { shortcut: (event: KeyboardEvent) => void; gesture: (gesture: ReaderGesture) => void }) {
  const keyboard = (event: KeyboardEvent) => {
    actions.shortcut(event);
    if (!document.getSelection()?.isCollapsed) return;
    const direction = readerKeyboardDirection(event);
    if (direction) { event.preventDefault(); turn(direction); }
  };
  const stopGestures = bindReaderGestures(document, { turn: direction => { if (isPaged(document)) turn(direction); }, onGesture: actions.gesture });
  document.addEventListener("keydown", keyboard);
  return () => { stopGestures(); document.removeEventListener("keydown", keyboard); };
}

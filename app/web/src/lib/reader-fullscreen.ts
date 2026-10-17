"use client";
import { useCallback, useEffect, useState, type RefObject } from "react";
export function useReaderFullscreen(target: RefObject<HTMLElement | null>) {
  const [active, setActive] = useState(false), [focus, setFocus] = useState(false), [supported, setSupported] = useState(false), [failed, setFailed] = useState(false);
  useEffect(() => {
    const update = () => setActive(document.fullscreenElement === document.documentElement);
    const timer = requestAnimationFrame(() => setSupported(document.fullscreenEnabled === true && !!target.current?.requestFullscreen));
    document.addEventListener("fullscreenchange", update);
    return () => { cancelAnimationFrame(timer); document.removeEventListener("fullscreenchange", update); };
  }, [target]);
  const toggle = useCallback(async () => {
    if (!supported) { setFocus(value => !value); return; }
    // Dialog portals share the document's fullscreen context.
    try { if (document.fullscreenElement === document.documentElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); setFailed(false); }
    catch { setFailed(true); }
  }, [supported]);
  const keyboard = useCallback((event: KeyboardEvent) => {
    if (event.defaultPrevented || event.repeat || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || target.current?.querySelector("dialog[open]")) return;
    if ((event.target as Element | null)?.closest?.('input,textarea,select,[contenteditable="true"],[contenteditable=""]')) return;
    if (event.key.toLowerCase() === "f") { event.preventDefault(); void toggle(); }
    if (event.key === "Escape") { setFocus(false); if (document.fullscreenElement) void toggle(); }
  }, [target, toggle]);
  return { active, focus, supported, failed, toggle, keyboard };
}

"use client";

import { SiteText } from "@/components/site-language";

import { useEffect, useRef, useState } from "react";
import type { ReaderAppearance } from "@/lib/reader-document";
import { bindReaderFrame, type FrameLocation } from "@/lib/reader-frame-binding";
import type { ReadingPosition } from "@/lib/reading-position";
import type { ReaderGesture } from "@/lib/reader-gestures";

type FrameProps = { src: string; title: string; appearance: ReaderAppearance; position: ReadingPosition; onPosition: (position: ReadingPosition) => void; onNavigate: (target: URL) => boolean; onDocument: (document: Document) => void; onPage: (direction: number) => void; onShortcut: (event: KeyboardEvent) => void; onGesture: (gesture: ReaderGesture) => void };

export function ReaderFrame({ src, title, appearance, position, onPosition, onNavigate, onDocument, onPage, onShortcut, onGesture }: FrameProps) {
  const frame = useRef<HTMLIFrameElement>(null);
  const location = useRef<FrameLocation>({ fraction: position.offset, anchor: null });
  const [failed, setFailed] = useState(false);
  const [restoreFailed, setRestoreFailed] = useState(false);
  const [ready, setReady] = useState(false);
  const [external, setExternal] = useState<string | null>(null);
  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    let cleanup: (() => void) | undefined;
    const loaded = () => { cleanup?.(); cleanup = bindReaderFrame(element,
      { src, appearance, position, onPosition, onNavigate, onDocument, onPage, onShortcut, onGesture, onExternal: setExternal, onReady: () => setReady(true), onFailure: () => setFailed(true), onRestoreFailure: () => setRestoreFailed(true) }, location.current); };
    element.addEventListener("load", loaded);
    const ready = requestAnimationFrame(() => { if (element.contentDocument?.readyState === "complete") loaded(); });
    return () => { cancelAnimationFrame(ready); element.removeEventListener("load", loaded); cleanup?.(); };
  }, [appearance, onNavigate, onPosition, onDocument, onPage, onShortcut, onGesture, position, src]);
  return <>{failed && <p className="notice" role="alert"><SiteText>{"অধ্যায়টি পাওয়া যায়নি। সংযোগ ও পড়ার অনুমতি পরীক্ষা করুন।"}</SiteText></p>}
    {(restoreFailed || position.restoration === "missing") && <p className="notice" role="alert"><SiteText>আগের সংরক্ষিত জায়গাটি এই সংস্করণে পাওয়া যায়নি। আপনার নোট সংরক্ষিত আছে।</SiteText></p>}
    {!ready && !failed && <p className="muted" role="status"><SiteText>{"অধ্যায়টি খোলা হচ্ছে…"}</SiteText></p>}
    {external && <p className="notice"><SiteText>{"বইয়ের বাইরের লিংক: "}</SiteText><a className="text-link" href={external} target="_blank" rel="noopener noreferrer"><SiteText>{"নতুন ট্যাবে খুলুন"}</SiteText></a></p>}
    {/* CSP blocks all authored scripts; the sandbox permits the parent's reader event handlers in WebKit. */}
    <iframe ref={frame} className="reader-frame" src={src} title={title} sandbox="allow-same-origin allow-scripts" aria-busy={!ready} referrerPolicy="no-referrer" /></>;
}

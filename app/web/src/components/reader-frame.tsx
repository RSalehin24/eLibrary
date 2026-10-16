"use client";

import { useEffect, useRef, useState } from "react";
import type { ReaderAppearance } from "@/lib/reader-document";
import { bindReaderFrame, type FrameLocation } from "@/lib/reader-frame-binding";
import type { ReadingPosition } from "@/lib/reading-position";

type FrameProps = { src: string; title: string; appearance: ReaderAppearance; position: ReadingPosition; onPosition: (position: ReadingPosition) => void; onNavigate: (target: URL) => boolean; onDocument: (document: Document) => void };

export function ReaderFrame({ src, title, appearance, position, onPosition, onNavigate, onDocument }: FrameProps) {
  const frame = useRef<HTMLIFrameElement>(null);
  const location = useRef<FrameLocation>({ fraction: position.offset, anchor: null });
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);
  const [external, setExternal] = useState<string | null>(null);
  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    let cleanup: (() => void) | undefined;
    const loaded = () => { cleanup?.(); cleanup = bindReaderFrame(element,
      { src, appearance, position, onPosition, onNavigate, onDocument, onExternal: setExternal, onReady: () => setReady(true), onFailure: () => setFailed(true) }, location.current); };
    element.addEventListener("load", loaded);
    const ready = requestAnimationFrame(() => { if (element.contentDocument?.readyState === "complete") loaded(); });
    return () => { cancelAnimationFrame(ready); element.removeEventListener("load", loaded); cleanup?.(); };
  }, [appearance, onNavigate, onPosition, onDocument, position, src]);
  return <>{failed && <p className="notice" role="alert">অধ্যায়টি পাওয়া যায়নি। সংযোগ ও পড়ার অনুমতি পরীক্ষা করুন।</p>}
    {!ready && !failed && <p className="muted" role="status">অধ্যায়টি খোলা হচ্ছে…</p>}
    {external && <p className="notice">বইয়ের বাইরের লিংক: <a className="text-link" href={external} target="_blank" rel="noopener noreferrer">নতুন ট্যাবে খুলুন</a></p>}
    <iframe ref={frame} className="reader-frame" src={src} title={title} sandbox="allow-same-origin" aria-busy={!ready} referrerPolicy="no-referrer" /></>;
}

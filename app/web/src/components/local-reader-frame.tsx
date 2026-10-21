"use client";
import { useEffect, useRef, useState } from "react";
import { applyAppearance, restoreAnchor, visibleAnchor } from "@/lib/reader-document";
import { bindReaderInteraction } from "@/lib/reader-interaction";
import { turnReaderPage } from "@/lib/reader-pagination";
import type { ReaderAppearance } from "@/lib/reader-preferences";
import type { ReaderGesture } from "@/lib/reader-gestures";

type Props = { html: string; title: string; appearance: ReaderAppearance; fragment: string;
  onDocument: (document: Document) => void; onNavigate: (chapter: number, fragment?: string) => void;
  onBoundary: (direction: number) => void; onShortcut: (event: KeyboardEvent) => void; onGesture: (gesture: ReaderGesture) => void };

export function LocalReaderFrame(props: Props) {
  const frame = useRef<HTMLIFrameElement>(null), [document, setDocument] = useState<Document | null>(null);
  const { appearance, onDocument, onNavigate, onBoundary, onShortcut, onGesture } = props;
  useEffect(() => {
    if (!document) return;
    const anchor = visibleAnchor(document);
    applyAppearance(document, appearance); restoreAnchor(document, anchor, 0);
    onDocument(document);
    const navigate = (event: MouseEvent) => {
      const element = (event.target as Element)?.closest?.("a");
      if (!element) return;
      event.preventDefault();
      if (element.dataset.localChapter) onNavigate(Number(element.dataset.localChapter), decodeURIComponent(element.hash.slice(1)));
    };
    const stop = bindReaderInteraction(document, direction => { if (!turnReaderPage(document, direction)) onBoundary(direction); }, { shortcut: onShortcut, gesture: onGesture });
    document.addEventListener("click", navigate);
    return () => { stop(); document.removeEventListener("click", navigate); };
  }, [document, appearance, onDocument, onNavigate, onBoundary, onShortcut, onGesture]);
  // WebKit requires script permission for parent-installed reader handlers; the generated CSP blocks authored scripts.
  return <iframe ref={frame} className="reader-frame local-reader-frame" title={props.title} sandbox="allow-same-origin allow-scripts" srcDoc={props.html} onLoad={() => {
    const current = frame.current?.contentDocument;
    if (!current?.body) return;
    applyAppearance(current, props.appearance);
    if (props.fragment) current.getElementById(props.fragment)?.scrollIntoView();
    setDocument(current); props.onDocument(current);
  }} />;
}

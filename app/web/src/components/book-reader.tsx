"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import type { ReaderSession } from "@/api/types";
import { useReadingProgress } from "@/lib/reading-progress";
import { initialPosition, positionProgress, type ReadingPosition } from "@/lib/reading-position";
import { scrollFraction, type ReaderAppearance } from "@/lib/reader-document";
import { chapterFromURL } from "@/lib/reader-links";
import { ReaderFrame } from "./reader-frame";
import { ReaderSettings } from "./reader-settings";
import { ReaderAnnotations } from "./reader-annotations";

export function BookReader({ session }: { session: ReaderSession }) {
  const [view, setView] = useState(() => ({ position: initialPosition(session.reading_progress, session.chapters.length), sequence: 0 }));
  const { position } = view;
  const [document, setDocument] = useState<Document | null>(null);
  const measuredPosition = useRef(position);
  const [appearance, setAppearance] = useState<ReaderAppearance>({ fontSize: 20, theme: "paper" });
  const [percent, setPercent] = useState(session.reading_progress.progress_percent);
  const [panel, setPanel] = useState<"contents" | "settings">("contents");
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const captureProgress = useCallback(() => {
    const current = document?.documentElement.isConnected && chapterFromURL(new URL(document.URL), session.resource_base, session.chapters) === position.chapter
      ? { chapter: position.chapter, offset: scrollFraction(document) } : measuredPosition.current;
    return positionProgress(current, session.chapters.length);
  }, [document, position.chapter, session.resource_base, session.chapters]);
  const progress = useReadingProgress(session.id, captureProgress);
  const { queue } = progress;
  const chapter = session.chapters[position.chapter];
  const openPanel = (value: "contents" | "settings", trigger: HTMLButtonElement) => { opener.current = trigger; setPanel(value); dialog.current?.showModal(); };
  const recordPosition = useCallback((value: ReadingPosition) => { measuredPosition.current = value; const update = positionProgress(value, session.chapters.length); setPercent(update.progress_percent); queue(update); }, [queue, session.chapters.length]);
  const navigate = useCallback((index: number, fragment?: string) => { setView((previous) => ({ position: { chapter: index, offset: 0, fragment }, sequence: previous.sequence + 1 })); dialog.current?.close(); }, []);
  const followChapter = useCallback((target: URL) => { const index = chapterFromURL(target, session.resource_base, session.chapters); if (index < 0) return false; navigate(index, target.hash); return true; }, [navigate, session.resource_base, session.chapters]);
  return <section className="reader-workspace"><Link className="text-link" href="/my-books/">← আমার বই</Link>
    <h1>{session.book_title}</h1><div className="reader-toolbar"><button className="button button-quiet" onClick={(event) => openPanel("contents", event.currentTarget)}>সূচিপত্র</button>
      <button className="button button-quiet" onClick={(event) => openPanel("settings", event.currentTarget)}>পড়ার সেটিংস</button>
      <span className="muted">{Math.round(percent)}% পড়া হয়েছে</span></div>
    <div className="reader-save-status" aria-live="polite">{progress.status === "failed" ? <p className="notice" role="alert">পড়ার অবস্থান সংরক্ষণ হয়নি। <button className="button button-quiet" onClick={() => void progress.flush()}>আবার সংরক্ষণ করুন</button></p>
      : <span className="muted">{progress.status === "pending" ? "অবস্থান সংরক্ষণ হচ্ছে…" : "পড়ার অবস্থান সংরক্ষিত"}</span>}</div>
    <ReaderAnnotations context={{ session, chapter: position.chapter, document, getPosition: () => measuredPosition.current }} onNavigate={(target) => { setView((previous) => ({ position: target, sequence: previous.sequence + 1 })); }} />
    <ReaderFrame key={view.sequence} src={session.resource_base + chapter.path.split("/").map(encodeURIComponent).join("/")} title={chapter.label} appearance={appearance} position={position} onPosition={recordPosition} onNavigate={followChapter} onDocument={setDocument} />
    <nav className="reader-pagination" aria-label="অধ্যায় পরিবর্তন"><button className="button button-quiet" disabled={position.chapter === 0} onClick={() => navigate(position.chapter - 1)}>আগের অধ্যায়</button>
      <span>{chapter.label}</span><button className="button" disabled={position.chapter === session.chapters.length - 1} onClick={() => navigate(position.chapter + 1)}>পরের অধ্যায়</button></nav>
    <dialog className="reader-dialog" ref={dialog} onClose={() => opener.current?.focus()}><div className="reader-dialog-heading"><h2>{panel === "contents" ? "সূচিপত্র" : "পড়ার সেটিংস"}</h2>
      <button className="button button-quiet" onClick={() => dialog.current?.close()}>বন্ধ করুন</button></div>
      {panel === "contents" ? <nav aria-label="বইয়ের সূচিপত্র">{session.chapters.map((entry, index) => <button key={entry.path} className="reader-chapter" aria-current={index === position.chapter ? "page" : undefined} onClick={() => navigate(index)}>{entry.label}</button>)}</nav>
        : <ReaderSettings appearance={appearance} onChange={setAppearance} />}</dialog>
  </section>;
}

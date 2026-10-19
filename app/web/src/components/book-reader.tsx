"use client";
import { SiteText, SiteNav, SiteNumber, SiteLanguageSwitch } from "@/components/site-language";
import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import type { ReaderSession } from "@/api/types";
import { useReadingProgress } from "@/lib/reading-progress";
import { sessionInitialPosition, positionProgress, type ReadingPosition } from "@/lib/reading-position";
import { scrollFraction } from "@/lib/reader-document";
import { readerPageState, turnReaderPage, readerKeyboardDirection } from "@/lib/reader-pagination";
import { useReaderPreferences } from "@/lib/reader-preference-state";
import { readerAppearanceShortcut } from "@/lib/reader-preferences";
import { useReaderFullscreen } from "@/lib/reader-fullscreen";
import { chapterFromURL } from "@/lib/reader-links";
import { ReaderFrame } from "./reader-frame";
import { ReaderSettings } from "./reader-settings";
import { ReaderViewControls } from "./reader-view-controls";
import { ReaderAnnotations } from "./reader-annotations";
import { ReaderSearch } from "./reader-search";
import { ReaderContents } from "./reader-contents";
import { checkedReaderAppearance } from "@/lib/reader-preferences";
import type { ReaderGesture } from "@/lib/reader-gestures";
import { Icon } from "./icon";

export function BookReader({ session, initialPosition }: { session: ReaderSession; initialPosition?: ReadingPosition }) {
  const [view, setView] = useState(() => ({ position: initialPosition ?? sessionInitialPosition(session), sequence: 0 }));
  const { position } = view;
  const [document, setDocument] = useState<Document | null>(null);
  const measuredPosition = useRef(position), workspace = useRef<HTMLElement>(null);
  const { appearance, changeAppearance, storageError } = useReaderPreferences();
  const fullscreen = useReaderFullscreen(workspace);
  const fullscreenKeyboard = fullscreen.keyboard;
  const shortcut = useCallback((event: KeyboardEvent) => {
    if (workspace.current?.querySelector("dialog[open]")) return;
    const updated = readerAppearanceShortcut(event, appearance);
    if (updated) { event.preventDefault(); changeAppearance(updated); }
    else fullscreenKeyboard(event);
  }, [appearance, changeAppearance, fullscreenKeyboard]);
  const toggleFullscreen = fullscreen.toggle;
  const gesture = useCallback((action: ReaderGesture) => {
    if (workspace.current?.querySelector("dialog[open]")) return;
    if (action.kind === "immersive") { void toggleFullscreen(); return; }
    const themes = ["paper", "sepia", "dark"];
    changeAppearance(checkedReaderAppearance(action.kind === "text" ? { ...appearance, fontSize: appearance.fontSize + action.steps * 2 } : { ...appearance, theme: themes[(themes.indexOf(appearance.theme) + 1) % themes.length] }));
  }, [appearance, changeAppearance, toggleFullscreen]);
  const immersive = fullscreen.active || fullscreen.focus;
  const [percent, setPercent] = useState(session.reading_progress.progress_percent), [pages, setPages] = useState({ current: 1, total: 1 });
  const [panel, setPanel] = useState<"contents" | "settings">("contents");
  const dialog = useRef<HTMLDialogElement>(null), opener = useRef<HTMLButtonElement | null>(null);
  const captureProgress = useCallback(() => {
    const current = document?.documentElement.isConnected && chapterFromURL(new URL(document.URL), session.resource_base, session.chapters) === position.chapter
      ? { chapter: position.chapter, offset: scrollFraction(document) } : measuredPosition.current;
    return positionProgress(current, session.chapters.length);
  }, [document, position.chapter, session.resource_base, session.chapters]);
  const progress = useReadingProgress(session.id, captureProgress), { queue } = progress;
  const chapter = session.chapters[position.chapter];
  const openPanel = (value: "contents" | "settings", trigger: HTMLButtonElement) => { opener.current = trigger; setPanel(value); dialog.current?.showModal(); };
  const recordPosition = useCallback((value: ReadingPosition) => { measuredPosition.current = value; const update = positionProgress(value, session.chapters.length); setPercent(update.progress_percent); if (document) setPages(readerPageState(document)); queue(update); }, [queue, session.chapters.length, document]);
  const navigate = useCallback((index: number, fragment?: string) => { setView(previous => ({ position: { chapter: index, offset: 0, fragment }, sequence: previous.sequence + 1 })); dialog.current?.close(); }, []);
  const turn = useCallback((direction: number) => {
    if (!document || turnReaderPage(document, direction)) return;
    const next = position.chapter + direction;
    if (next >= 0 && next < session.chapters.length) setView(previous => ({ position: { chapter: next, offset: direction < 0 ? 1 : 0 }, sequence: previous.sequence + 1 }));
  }, [document, position.chapter, session.chapters.length]);
  const followChapter = useCallback((target: URL) => { const index = chapterFromURL(target, session.resource_base, session.chapters); if (index < 0) return false; navigate(index, target.hash); return true; }, [navigate, session.resource_base, session.chapters]);
  return <section ref={workspace} className={`reader-workspace${fullscreen.focus ? " reader-focus-mode" : ""}${immersive ? " reader-immersive" : ""}`} data-reader-theme={appearance.theme} onKeyDown={event => { if (event.currentTarget.querySelector("dialog[open]")) return; shortcut(event.nativeEvent); const direction = readerKeyboardDirection(event.nativeEvent); if (direction) { event.preventDefault(); turn(direction); } }}>
    <header className="reader-header"><Link className="text-link" href="/my-books/"><SiteText>← আমার বই</SiteText></Link><h1>{session.book_title}</h1><SiteLanguageSwitch /><button className="button button-quiet" onClick={() => { void fullscreen.toggle(); }}><SiteText>{fullscreen.supported ? fullscreen.active ? "পূর্ণ পর্দা থেকে ফিরুন" : "পূর্ণ পর্দা" : fullscreen.focus ? "সাধারণ দৃশ্যে ফিরুন" : "শুধু বই দেখুন"}</SiteText></button></header>
    <div className="reader-toolbar"><button className="button button-quiet" onClick={event => openPanel("contents", event.currentTarget)}><Icon name="books" /><span className="reader-action-label"><SiteText>সূচিপত্র</SiteText></span></button><button className="button button-quiet" onClick={event => openPanel("settings", event.currentTarget)}><Icon name="settings" /><span className="reader-action-label"><SiteText>পড়ার সেটিংস</SiteText></span></button><ReaderSearch session={session} onNavigate={target => setView(previous => ({ position: target, sequence: previous.sequence + 1 }))} />    <ReaderAnnotations context={{ session, chapter: position.chapter, document, getPosition: () => measuredPosition.current }} onNavigate={target => setView(previous => ({ position: target, sequence: previous.sequence + 1 }))} /></div>
    {(storageError || fullscreen.failed) && <p className="notice" role="alert"><SiteText>{fullscreen.failed ? "পূর্ণ পর্দা চালু করা যায়নি। আবার চেষ্টা করুন।" : "এই ব্রাউজারে পড়ার সেটিংস সংরক্ষণ করা যায়নি।"}</SiteText></p>}

    <ReaderFrame key={view.sequence} src={session.resource_base + chapter.path.split("/").map(encodeURIComponent).join("/")} title={chapter.label} appearance={appearance} position={position} onPosition={recordPosition} onNavigate={followChapter} onDocument={setDocument} onPage={turn} onShortcut={shortcut} onGesture={gesture} />
    {appearance.view !== "scroll" && <SiteNav className="reader-page-navigation" aria-label="পাতা পরিবর্তন"><button className="button button-quiet" disabled={position.chapter === 0 && pages.current <= 1} onClick={() => turn(-1)}><SiteText>আগের পাতা</SiteText></button><span><SiteText>পাতা</SiteText> <SiteNumber value={pages.current} /> / <SiteNumber value={pages.total} /></span><button className="button" disabled={position.chapter === session.chapters.length - 1 && pages.current >= pages.total} onClick={() => turn(1)}><SiteText>পরের পাতা</SiteText></button></SiteNav>}
    <SiteNav className="reader-pagination" aria-label="অধ্যায় পরিবর্তন"><button className="button button-quiet" disabled={position.chapter === 0} onClick={() => navigate(position.chapter - 1)}><SiteText>আগের অধ্যায়</SiteText></button><span>{chapter.label}</span><button className="button button-quiet" disabled={position.chapter === session.chapters.length - 1} onClick={() => navigate(position.chapter + 1)}><SiteText>পরের অধ্যায়</SiteText></button></SiteNav>
    <div className="reader-save-status" aria-live="polite"><span><SiteNumber value={Math.round(percent)} /><SiteText>% পড়া হয়েছে</SiteText></span>{progress.status === "failed" ? <p className="notice" role="alert"><SiteText>পড়ার অবস্থান সংরক্ষণ হয়নি। </SiteText><button className="button button-quiet" onClick={() => void progress.flush()}><SiteText>আবার সংরক্ষণ করুন</SiteText></button></p> : <span className="muted"><SiteText>{progress.status === "pending" ? "অবস্থান সংরক্ষণ হচ্ছে…" : "পড়ার অবস্থান সংরক্ষিত"}</SiteText></span>}</div>
    <dialog className="reader-dialog" ref={dialog} onClose={() => opener.current?.focus()}><div className="reader-dialog-heading"><h2><SiteText>{panel === "contents" ? "সূচিপত্র" : "পড়ার সেটিংস"}</SiteText></h2><button className="button button-quiet" onClick={() => dialog.current?.close()}><SiteText>বন্ধ করুন</SiteText></button></div>{panel === "contents" ? <SiteNav aria-label="বইয়ের সূচিপত্র"><ReaderContents session={session} chapter={position.chapter} onNavigate={navigate} /></SiteNav> : <><ReaderViewControls appearance={appearance} onChange={changeAppearance} /><ReaderSettings appearance={appearance} onChange={changeAppearance} /></>}</dialog>
  </section>;
}

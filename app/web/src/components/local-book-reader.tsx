"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SiteLanguageSwitch, SiteNumber, SiteText, useSiteLanguage } from "./site-language";
import { FilePicker } from "./file-picker";
import { ReaderSettings } from "./reader-settings";
import { ReaderViewControls } from "./reader-view-controls";
import { LocalReaderFrame } from "./local-reader-frame";
import { ContentsList } from "./reader-contents";
import { useReaderPreferences } from "@/lib/reader-preference-state";
import { useReaderFullscreen } from "@/lib/reader-fullscreen";
import { checkedReaderAppearance, readerAppearanceShortcut } from "@/lib/reader-preferences";
import { turnReaderPage } from "@/lib/reader-pagination";
import type { ReaderGesture } from "@/lib/reader-gestures";
import { openLocalBook } from "@/lib/local-epub/open";
import type { LocalBookResources } from "@/lib/local-epub/resources";
import { Icon } from "./icon";
import { ReaderFontControls } from "./reader-font-controls";
import { activateReaderTool } from "@/lib/reader-shortcuts";
import "./local-reader-start.css";

export function LocalBookReader() {
  const [book, setBook] = useState<LocalBookResources | null>(null), [loading, setLoading] = useState(false), [error, setError] = useState(false);
  const [position, setPosition] = useState({ chapter: 0, fragment: "", sequence: 0 }), [panel, setPanel] = useState<"contents" | "settings">("contents");
  const workspace = useRef<HTMLElement>(null), dialog = useRef<HTMLDialogElement>(null), document = useRef<Document | null>(null), generation = useRef(0);
  const { appearance, changeAppearance, storageError } = useReaderPreferences(), fullscreen = useReaderFullscreen(workspace), { t } = useSiteLanguage();
  useEffect(() => () => book?.dispose(), [book]);
  useEffect(() => () => { generation.current += 1; }, []);
  const html = useMemo(() => {
    if (!book) return "";
    try { return book.chapter(position.chapter); } catch { return ""; }
  }, [book, position.chapter]);
  const navigate = useCallback((chapter: number, fragment = "") => {
    if (!book || chapter < 0 || chapter >= book.book.chapters.length) return;
    setPosition(previous => ({ chapter, fragment, sequence: previous.sequence + 1 })); dialog.current?.close();
  }, [book]);
  const turn = useCallback((direction: number) => { if (!document.current || !turnReaderPage(document.current, direction)) navigate(position.chapter + direction); }, [navigate, position.chapter]);
  const shortcut = useCallback((event: KeyboardEvent) => {
    if (dialog.current?.open) return;
    activateReaderTool(event, workspace.current);
    const updated = readerAppearanceShortcut(event, appearance);
    if (updated) { event.preventDefault(); changeAppearance(updated); } else fullscreen.keyboard(event);
  }, [appearance, changeAppearance, fullscreen]);
  const gesture = useCallback((action: ReaderGesture) => {
    if (dialog.current?.open) return;
    if (action.kind === "immersive") { void fullscreen.toggle(); return; }
    const themes = ["paper", "sepia", "dark"];
    changeAppearance(checkedReaderAppearance(action.kind === "text" ? { ...appearance, fontSize: appearance.fontSize + action.steps * 2 } : { ...appearance, theme: themes[(themes.indexOf(appearance.theme) + 1) % 3] }));
  }, [appearance, changeAppearance, fullscreen]);
  const recordDocument = useCallback((current: Document) => { document.current = current; }, []);
  async function open(file?: File) {
    if (!file) return;
    const identifier = ++generation.current;
    setLoading(true); setError(false);
    try {
      const opened = await openLocalBook(file);
      if (identifier !== generation.current) { opened.dispose(); return; }
      setPosition({ chapter: 0, fragment: "", sequence: 0 }); setBook(opened);
    } catch { if (identifier === generation.current) setError(true); }
    finally { if (identifier === generation.current) setLoading(false); }
  }
  const immersive = fullscreen.active || fullscreen.focus;
  const chapter = book?.book.chapters[position.chapter];
  const navigation = book?.book.navigation.length ? book.book.navigation : book?.book.chapters.map((item, index) => ({ label: `${t("অধ্যায়")} ${index + 1}`, chapter_index: index, fragment: "", depth: 0 })) ?? [];
  return <section ref={workspace} className={book ? `reader-workspace${fullscreen.focus ? " reader-focus-mode" : ""}${immersive ? " reader-immersive" : ""}` : "local-reader-start"} data-reader-theme={appearance.theme} onKeyDown={event => shortcut(event.nativeEvent)}>
    <header className={book ? "reader-header" : "local-reader-heading"}>{!book && <Icon name="read" size={32} />}<h1 title={book?.book.title}>{book?.book.title ?? t("নিজের EPUB পড়ুন")}</h1>{book && <><SiteLanguageSwitch /><button className="button button-quiet reader-close" onClick={() => { generation.current += 1; setBook(null); document.current = null; }}><Icon name="close" /><span><SiteText>বই বন্ধ করুন</SiteText></span></button><button className="button button-quiet reader-fullscreen" aria-keyshortcuts="f" onClick={() => void fullscreen.toggle()}><Icon name="fullscreen" /><span><SiteText>{fullscreen.supported ? "পূর্ণ পর্দা" : "শুধু বই দেখুন"}</SiteText></span></button></>}</header>
    {!book && <><p><SiteText>আপনার ডিভাইসের EPUB ফাইল খুলুন। ফাইলটি এই ব্রাউজারেই পড়া হবে; সার্ভারে পাঠানো বা অ্যাকাউন্টে সংরক্ষণ করা হবে না।</SiteText></p><p><SiteText>এই পাতা একবার প্রস্তুত হলে ইন্টারনেট ছাড়াও নিজের EPUB খুলতে পারবেন।</SiteText></p><div className="local-reader-upload"><label htmlFor="local-epub"><Icon name="upload" /><SiteText>EPUB ফাইল বেছে নিন</SiteText></label><FilePicker id="local-epub" accept=".epub,application/epub+zip" aria-describedby="local-epub-help" disabled={loading} onChange={event => void open(event.target.files?.[0])} /><p className="muted" id="local-epub-help"><SiteText>সর্বোচ্চ ২৪ MiB। পাসওয়ার্ড বা DRM দিয়ে সুরক্ষিত বই খোলা যাবে না।</SiteText></p></div></>}
    {loading && <p role="status"><SiteText>বই খোলা হচ্ছে…</SiteText></p>}
    {error && <p className="notice" role="alert"><SiteText>এই EPUB খোলা যায়নি। সম্পূর্ণ ও সুরক্ষামুক্ত EPUB ফাইল দিন; আকার সর্বোচ্চ ২৪ MiB।</SiteText></p>}
    {book && <><div className="reader-toolbar"><button className="button button-quiet reader-panel-action" data-reader-tool="contents" aria-keyshortcuts="t" onClick={() => { setPanel("contents"); dialog.current?.showModal(); }}><Icon name="books" /><span className="reader-action-label"><SiteText>সূচিপত্র</SiteText></span></button><ReaderFontControls appearance={appearance} onChange={changeAppearance} /><button className="button button-quiet reader-panel-action" data-reader-tool="settings" aria-keyshortcuts="s" onClick={() => { setPanel("settings"); dialog.current?.showModal(); }}><Icon name="settings" /><span className="reader-action-label"><SiteText>পড়ার সেটিংস</SiteText></span></button></div>
      {html ? <LocalReaderFrame key={position.sequence} html={html} title={book.book.title} appearance={appearance} fragment={position.fragment} onDocument={recordDocument} onNavigate={navigate} onBoundary={direction => navigate(position.chapter + direction)} onShortcut={shortcut} onGesture={gesture} /> : <p className="notice" role="alert"><SiteText>এই অধ্যায়টি খোলা যায়নি। অন্য অধ্যায় বেছে নিন।</SiteText></p>}
      <nav className="reader-pagination" aria-label={t("অধ্যায় পরিবর্তন")}><button className="button button-quiet" disabled={position.chapter === 0} onClick={() => navigate(position.chapter - 1)}><SiteText>আগের অধ্যায়</SiteText></button><span><SiteText>অধ্যায়</SiteText> <SiteNumber value={position.chapter + 1} /> / <SiteNumber value={book.book.chapters.length} /></span><button className="button" disabled={!chapter || position.chapter === book.book.chapters.length - 1} onClick={() => navigate(position.chapter + 1)}><SiteText>পরের অধ্যায়</SiteText></button></nav>
      {appearance.view !== "scroll" && <nav className="reader-page-navigation" aria-label={t("পাতা পরিবর্তন")}><button className="button button-quiet" onClick={() => turn(-1)}><SiteText>আগের পাতা</SiteText></button><button className="button" onClick={() => turn(1)}><SiteText>পরের পাতা</SiteText></button></nav>}
      <dialog ref={dialog} className="reader-dialog"><div className="reader-dialog-heading"><h2><SiteText>{panel === "contents" ? "সূচিপত্র" : "পড়ার সেটিংস"}</SiteText></h2><button className="button button-quiet" onClick={() => dialog.current?.close()}><SiteText>বন্ধ করুন</SiteText></button></div>{panel === "contents" ? <ContentsList entries={navigation} chapter={position.chapter} onNavigate={navigate} /> : <><ReaderViewControls appearance={appearance} onChange={changeAppearance} /><ReaderSettings appearance={appearance} onChange={changeAppearance} /></>}</dialog></>}
    {(storageError || fullscreen.failed) && <p role="alert"><SiteText>{fullscreen.failed ? "পূর্ণ পর্দা চালু করা যায়নি। আবার চেষ্টা করুন।" : "এই ব্রাউজারে পড়ার সেটিংস সংরক্ষণ করা যায়নি।"}</SiteText></p>}
  </section>;
}

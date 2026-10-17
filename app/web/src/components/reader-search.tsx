"use client";
import { useEffect, useRef, useState } from "react";
import type { ReaderSession } from "@/api/types";
import type { ReadingPosition } from "@/lib/reading-position";
import { chapterMatches, inertChapterText, type ReaderMatch } from "@/lib/reader-search";
import { readChapterText } from "@/api/reader-search";
import { SiteText, SiteNumber, SiteInput } from "./site-language";
import { Icon } from "./icon";
export function ReaderSearch({ session, onNavigate }: { session: ReaderSession; onNavigate: (target: ReadingPosition) => void }) {
  const dialog = useRef<HTMLDialogElement>(null), abort = useRef<AbortController | null>(null), opener = useRef<HTMLButtonElement>(null);
  const [query, setQuery] = useState(""), [results, setResults] = useState<ReaderMatch[]>([]), [busy, setBusy] = useState(false), [failed, setFailed] = useState(false), [searched, setSearched] = useState(false);
  useEffect(() => () => abort.current?.abort(), []);
  async function search() {
    abort.current?.abort(); const controller = new AbortController(); abort.current = controller;
    setBusy(true); setFailed(false); setSearched(true); setResults([]); const found: ReaderMatch[] = [];
    try {
      for (let chapter = 0; chapter < session.chapters.length && found.length < 100; chapter++) {
        const text = inertChapterText(await readChapterText(session.resource_base + session.chapters[chapter].path.split("/").map(encodeURIComponent).join("/"), controller.signal));
        found.push(...chapterMatches(text, query, chapter));
        if (!controller.signal.aborted) setResults(found.slice(0, 100));
      }
    } catch { if (!controller.signal.aborted) setFailed(true); }
    finally { if (abort.current === controller) setBusy(false); }
  }
  return <><button className="button button-quiet" ref={opener} onClick={() => dialog.current?.showModal()}><Icon name="search" /><span className="reader-action-label"><SiteText>বইয়ে খুঁজুন</SiteText></span></button><dialog className="reader-dialog" ref={dialog} onClose={() => { abort.current?.abort(); setBusy(false); opener.current?.focus(); }}><div className="reader-dialog-heading"><h2><SiteText>বইয়ে খুঁজুন</SiteText></h2><button className="button button-quiet" onClick={() => dialog.current?.close()}><SiteText>বন্ধ করুন</SiteText></button></div>
    <form className="search-form" onSubmit={event => { event.preventDefault(); void search(); }}><label className="visually-hidden" htmlFor="reader-search"><SiteText>শব্দ বা বাক্য</SiteText></label><SiteInput id="reader-search" value={query} onChange={event => setQuery(event.target.value)} placeholder="শব্দ বা বাক্য" minLength={2} maxLength={100} required /><button className="button" disabled={busy}><SiteText>খুঁজুন</SiteText></button></form>
    {busy && <p role="status"><SiteText>বইয়ে খোঁজা হচ্ছে…</SiteText></p>}{failed && <p role="alert" className="notice"><SiteText>সব অধ্যায়ে খোঁজা যায়নি। আবার চেষ্টা করুন।</SiteText></p>}
    {searched && !busy && !failed && !results.length && <p><SiteText>কোনো মিল পাওয়া যায়নি।</SiteText></p>}
    {!!results.length && <p><SiteNumber value={results.length} /><SiteText>টি মিল পাওয়া গেছে (সর্বোচ্চ ১০০)।</SiteText></p>}
    <ol className="reader-search-results">{results.map(result => <li key={`${result.chapter}:${result.start}`}><button className="reader-chapter" onClick={() => { onNavigate({ chapter: result.chapter, offset: 0, selection: { start: result.start, end: result.end } }); dialog.current?.close(); }}><strong>{session.chapters[result.chapter].label}</strong><span>{result.excerpt}</span></button></li>)}</ol>
    </dialog></>;
}

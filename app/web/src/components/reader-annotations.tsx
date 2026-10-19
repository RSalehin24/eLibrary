"use client";

import { SiteText } from "@/components/site-language";

import Link from "next/link";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { readerBookmarks, readerHighlights, saveBookmark } from "@/api/annotations";
import type { Highlight, ReaderSession } from "@/api/types";
import { applyHighlights, jumpToHighlight, selectedText, type TextSelection } from "@/lib/reader-annotations";
import { observeReaderDocument } from "@/lib/reader-observation";
import { initialPosition, legacyChapter, positionProgress, type ReadingPosition } from "@/lib/reading-position";
import { chapterFromURL } from "@/lib/reader-links";
import { captureBookmarkText } from "@/lib/bookmark-text-anchor";
import { annotationPosition } from "@/lib/annotation-position";
import { HighlightForm } from "./highlight-form";
import { Icon } from "./icon";

type AnnotationContext = { session: ReaderSession; chapter: number; document: Document | null; getPosition: () => ReadingPosition };

export function ReaderAnnotations({ context, onNavigate }: { context: AnnotationContext; onNavigate: (position: ReadingPosition) => void }) {
  const { session, chapter } = context;
  const document = context.document && chapterFromURL(new URL(context.document.URL), session.resource_base, session.chapters) === chapter ? context.document : null;
  const [panel, setPanel] = useState<"list" | "selection">("list");
  const [captured, setSelection] = useState<(TextSelection & { document: Document }) | null>(null);
  const selection = captured?.document === document ? captured : null;
  const dialog = useRef<HTMLDialogElement>(null);
  const resolved = useRef(new Map<string, { start: number; end: number }>());
  const queries = useQueryClient();
  const bookmarks = useInfiniteQuery({ queryKey: ["annotations", "reader", session.id, "bookmarks"], initialPageParam: "", queryFn: ({ signal, pageParam }) => readerBookmarks(session.id, { cursor: pageParam, signal }), getNextPageParam: (page) => page.next_cursor ?? undefined });
  const highlights = useInfiniteQuery({ queryKey: ["annotations", "reader", session.id, "highlights"], initialPageParam: "", queryFn: ({ signal, pageParam }) => readerHighlights(session.id, { cursor: pageParam, signal }), getNextPageParam: (page) => page.next_cursor ?? undefined });
  const save = useMutation({ mutationFn: () => saveBookmark(session.id, { ...(document && captureBookmarkText(document, chapter) || { location: positionProgress(context.getPosition(), session.chapters.length).last_location }), chapter_href: session.chapters[chapter].path, chapter_label: session.chapters[chapter].label }), retry: false, onSuccess: () => queries.invalidateQueries({ queryKey: ["annotations"] }) });
  useEffect(() => {
    if (!document) return;
    const capture = () => {
      const value = selectedText(document);
      setSelection((previous) => {
        if (previous?.document === document && previous.selector.start === value?.selector.start && previous.selector.end === value?.selector.end) return previous;
        return value ? { ...value, document } : null;
      });
    };
    return observeReaderDocument(document, capture);
  }, [document]);
  useEffect(() => { if (document) resolved.current = applyHighlights(document, highlights.data?.pages.flatMap((page) => page.entries).filter(entry => legacyChapter(entry.legacy_cfi || entry.chapter_href, session.chapters) === chapter) ?? []); }, [document, highlights.data, chapter, session.chapters]);
  const open = (value: "list" | "selection") => { setPanel(value); dialog.current?.showModal(); };
  const follow = (annotation: Highlight) => { const index = legacyChapter(annotation.legacy_cfi || annotation.chapter_href, session.chapters); const selector = resolved.current.get(annotation.id) ?? annotation.selector; if (index === chapter && document && jumpToHighlight(document, { ...annotation, selector })) { dialog.current?.close(); return; } onNavigate(index >= 0 ? annotationPosition(annotation, session) : { ...context.getPosition(), restoration: "missing" }); dialog.current?.close(); };
  return <><div className="annotation-actions"><button className="button button-quiet" disabled={save.isPending || !document} onClick={() => save.mutate()}><Icon name="bookmark" /><span className="reader-action-label"><SiteText>{"এখানে বুকমার্ক রাখুন"}</SiteText></span></button>
    <button className="button button-quiet" onClick={() => open("list")}><Icon name="books" /><span className="reader-action-label"><SiteText>{"বুকমার্ক ও দাগ"}</SiteText></span></button><Link className="text-link" href="/notes/"><Icon name="notes" /><span className="reader-action-label"><SiteText>{"নিজের সব নোট →"}</SiteText></span></Link>
    {selection && <button className="button" onClick={() => open("selection")}><Icon name="edit" /><span className="reader-action-label"><SiteText>{"নির্বাচিত লেখায় দাগ দিন"}</SiteText></span></button>}</div>
    <div aria-live="polite">{save.isSuccess && <><p className="muted"><SiteText>{"বুকমার্ক সংরক্ষিত"}</SiteText></p>{save.data.location.startsWith("chapter:") && <p className="notice"><SiteText>এই জায়গায় লেখার অবস্থান ধরা যায়নি। বুকমার্কে পাতার আনুমানিক অবস্থান রাখা হয়েছে।</SiteText></p>}</>}{save.isError && <p className="notice" role="alert"><SiteText>{"বুকমার্ক সংরক্ষণ হয়নি। আবার চেষ্টা করুন।"}</SiteText></p>}</div>
    <dialog className="reader-dialog" ref={dialog}><div className="reader-dialog-heading"><h2>{panel === "list" ? <SiteText>{"বুকমার্ক ও দাগ"}</SiteText> : <SiteText>{"দাগ ও নোট"}</SiteText>}</h2><button className="button button-quiet" onClick={() => dialog.current?.close()}><SiteText>{"বন্ধ করুন"}</SiteText></button></div>
      {panel === "selection" && selection ? <HighlightForm key={selection.selector.start + ":" + selection.selector.end} context={{ session, chapter }} selection={selection} onSaved={() => { dialog.current?.close(); setSelection(null); }} /> : <>
        {(bookmarks.isPending || highlights.isPending) && <p role="status"><SiteText>{"তথ্য পাওয়া হচ্ছে…"}</SiteText></p>}{(bookmarks.isError || highlights.isError) && <p className="notice" role="alert"><SiteText>{"তথ্য পাওয়া যায়নি। "}</SiteText><button className="button button-quiet" onClick={() => { void bookmarks.refetch(); void highlights.refetch(); }}><SiteText>{"আবার চেষ্টা করুন"}</SiteText></button></p>}
        <h3><SiteText>{"বুকমার্ক"}</SiteText></h3>{bookmarks.data?.pages.flatMap((page) => page.entries).map((entry) => <button className="reader-chapter" data-bookmark-id={entry.id} key={entry.id} onClick={() => { onNavigate(initialPosition({ last_location: entry.location, progress_percent: 0 }, session.chapters)); dialog.current?.close(); }}>{entry.chapter_label || entry.label || <SiteText>{"সংরক্ষিত অবস্থান"}</SiteText>}{entry.preview_text && <><br /><span>{entry.preview_text}</span></>}</button>)}
        {bookmarks.hasNextPage && <button className="button button-quiet" disabled={bookmarks.isFetchingNextPage} onClick={() => void bookmarks.fetchNextPage()}><SiteText>{"আরও বুকমার্ক"}</SiteText></button>}
        <h3><SiteText>{"দাগ ও উদ্ধৃতি"}</SiteText></h3>{highlights.data?.pages.flatMap((page) => page.entries).map((entry) => <button className="reader-chapter" key={entry.id} onClick={() => follow(entry)}>{entry.chapter_label}<br />{entry.text.slice(0, 140)}</button>)}
        {highlights.hasNextPage && <button className="button button-quiet" disabled={highlights.isFetchingNextPage} onClick={() => void highlights.fetchNextPage()}><SiteText>{"আরও দাগ"}</SiteText></button>}
      </>}
    </dialog></>;
}

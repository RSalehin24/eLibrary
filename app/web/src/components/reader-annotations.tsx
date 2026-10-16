"use client";

import Link from "next/link";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { readerBookmarks, readerHighlights, saveBookmark } from "@/api/annotations";
import type { Highlight, ReaderSession } from "@/api/types";
import { applyHighlights, jumpToHighlight, selectedText, type TextSelection } from "@/lib/reader-annotations";
import { observeReaderDocument } from "@/lib/reader-observation";
import { initialPosition, positionProgress, type ReadingPosition } from "@/lib/reading-position";
import { chapterFromURL } from "@/lib/reader-links";
import { HighlightForm } from "./highlight-form";

type AnnotationContext = { session: ReaderSession; chapter: number; document: Document | null; getPosition: () => ReadingPosition };

export function ReaderAnnotations({ context, onNavigate }: { context: AnnotationContext; onNavigate: (position: ReadingPosition) => void }) {
  const { session, chapter } = context;
  const document = context.document && chapterFromURL(new URL(context.document.URL), session.resource_base, session.chapters) === chapter ? context.document : null;
  const [panel, setPanel] = useState<"list" | "selection">("list");
  const [captured, setSelection] = useState<(TextSelection & { document: Document }) | null>(null);
  const selection = captured?.document === document ? captured : null;
  const dialog = useRef<HTMLDialogElement>(null);
  const queries = useQueryClient();
  const bookmarks = useInfiniteQuery({ queryKey: ["annotations", "reader", session.id, "bookmarks"], initialPageParam: "", queryFn: ({ signal, pageParam }) => readerBookmarks(session.id, { cursor: pageParam, signal }), getNextPageParam: (page) => page.next_cursor ?? undefined });
  const highlights = useInfiniteQuery({ queryKey: ["annotations", "reader", session.id, "highlights"], initialPageParam: "", queryFn: ({ signal, pageParam }) => readerHighlights(session.id, { cursor: pageParam, signal }), getNextPageParam: (page) => page.next_cursor ?? undefined });
  const save = useMutation({ mutationFn: () => saveBookmark(session.id, { location: positionProgress(context.getPosition(), session.chapters.length).last_location, chapter_href: session.chapters[chapter].path, chapter_label: session.chapters[chapter].label }), retry: false, onSuccess: () => queries.invalidateQueries({ queryKey: ["annotations"] }) });
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
  useEffect(() => { if (document) applyHighlights(document, highlights.data?.pages.flatMap((page) => page.entries).filter((entry) => entry.chapter_href === session.chapters[chapter].path) ?? []); }, [document, highlights.data, chapter, session.chapters]);
  const open = (value: "list" | "selection") => { setPanel(value); dialog.current?.showModal(); };
  const follow = (annotation: Highlight) => { const index = session.chapters.findIndex((entry) => entry.path === annotation.chapter_href); if (index === chapter && document && jumpToHighlight(document, annotation)) { dialog.current?.close(); return; } if (index >= 0) { onNavigate({ chapter: index, offset: 0, selection: annotation.selector ?? undefined }); dialog.current?.close(); } };
  return <><div className="annotation-actions"><button className="button button-quiet" disabled={save.isPending || !document} onClick={() => save.mutate()}>এখানে বুকমার্ক রাখুন</button>
    <button className="button button-quiet" onClick={() => open("list")}>বুকমার্ক ও দাগ</button><Link className="text-link" href="/notes/">নিজের সব নোট →</Link>
    {selection && <button className="button" onClick={() => open("selection")}>নির্বাচিত লেখায় দাগ দিন</button>}</div>
    <div aria-live="polite">{save.isSuccess && <p className="muted">বুকমার্ক সংরক্ষিত</p>}{save.isError && <p className="notice" role="alert">বুকমার্ক সংরক্ষণ হয়নি। আবার চেষ্টা করুন।</p>}</div>
    <dialog className="reader-dialog" ref={dialog}><div className="reader-dialog-heading"><h2>{panel === "list" ? "বুকমার্ক ও দাগ" : "দাগ ও নোট"}</h2><button className="button button-quiet" onClick={() => dialog.current?.close()}>বন্ধ করুন</button></div>
      {panel === "selection" && selection ? <HighlightForm key={selection.selector.start + ":" + selection.selector.end} context={{ session, chapter }} selection={selection} onSaved={() => { dialog.current?.close(); setSelection(null); }} /> : <>
        {(bookmarks.isPending || highlights.isPending) && <p role="status">তথ্য পাওয়া হচ্ছে…</p>}{(bookmarks.isError || highlights.isError) && <p className="notice" role="alert">তথ্য পাওয়া যায়নি। <button className="button button-quiet" onClick={() => { void bookmarks.refetch(); void highlights.refetch(); }}>আবার চেষ্টা করুন</button></p>}
        <h3>বুকমার্ক</h3>{bookmarks.data?.pages.flatMap((page) => page.entries).map((entry) => <button className="reader-chapter" key={entry.id} onClick={() => { onNavigate(initialPosition({ last_location: entry.location, progress_percent: 0 }, session.chapters.length)); dialog.current?.close(); }}>{entry.chapter_label || entry.label || "সংরক্ষিত অবস্থান"}</button>)}
        {bookmarks.hasNextPage && <button className="button button-quiet" disabled={bookmarks.isFetchingNextPage} onClick={() => void bookmarks.fetchNextPage()}>আরও বুকমার্ক</button>}
        <h3>দাগ ও উদ্ধৃতি</h3>{highlights.data?.pages.flatMap((page) => page.entries).map((entry) => <button className="reader-chapter" key={entry.id} onClick={() => follow(entry)}>{entry.chapter_label}<br />{entry.text.slice(0, 140)}</button>)}
        {highlights.hasNextPage && <button className="button button-quiet" disabled={highlights.isFetchingNextPage} onClick={() => void highlights.fetchNextPage()}>আরও দাগ</button>}
      </>}
    </dialog></>;
}

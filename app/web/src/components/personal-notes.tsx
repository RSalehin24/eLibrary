"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { personalAnnotation, personalAnnotations, type AnnotationKind } from "@/api/annotations";
import type { AnnotationSummary } from "@/api/types";
import { AnnotationNote } from "./annotation-note";

export function PersonalNotes() {
  const [kind, setKind] = useState<AnnotationKind>("highlights");
  const [selected, setSelected] = useState<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const records = useInfiniteQuery({ queryKey: ["annotations", "personal", kind], initialPageParam: "", queryFn: ({ pageParam, signal }) => personalAnnotations(kind, { cursor: pageParam, signal }), getNextPageParam: (page) => page.next_cursor ?? undefined });
  const detail = useQuery({ queryKey: ["annotations", "detail", kind, selected], queryFn: ({ signal }) => personalAnnotation(kind, selected!, signal), enabled: selected !== null });
  const close = () => { dialog.current?.close(); setSelected(null); };
  return <section><div className="annotation-actions" role="group" aria-label="নোটের ধরন"><button className="button button-quiet" aria-pressed={kind === "highlights"} onClick={() => setKind("highlights")}>দাগ ও উদ্ধৃতি</button>
    <button className="button button-quiet" aria-pressed={kind === "bookmarks"} onClick={() => setKind("bookmarks")}>বুকমার্ক</button></div>
    {records.isPending && <p role="status">নোট পাওয়া হচ্ছে…</p>}
    {records.isError && <p className="notice" role="alert">নোট পাওয়া যায়নি। <button className="button button-quiet" onClick={() => void records.refetch()}>আবার চেষ্টা করুন</button></p>}
    <div className="annotation-list">{records.data?.pages.flatMap<AnnotationSummary>((page) => page.entries).map((annotation) => <button className="annotation-card" data-annotation-id={annotation.id} key={annotation.id} onClick={() => { setSelected(annotation.id); dialog.current?.showModal(); }}>
      <strong>{annotation.book_title}</strong><span>{annotation.chapter_label}</span><span>{"text_preview" in annotation ? annotation.text_preview : annotation.preview_text}</span><span>{annotation.note_preview}</span><span className="text-link">নোট খুলুন →</span>
    </button>)}</div>
    {records.data && records.data.pages[0].entries.length === 0 && <p className="empty-state">এখনও কোনো {kind === "bookmarks" ? "বুকমার্ক" : "দাগ বা উদ্ধৃতি"} নেই। বই পড়ার সময় এগুলো তৈরি করতে পারবেন।</p>}
    {records.hasNextPage && <button className="button button-quiet" disabled={records.isFetchingNextPage} onClick={() => void records.fetchNextPage()}>আরও দেখুন</button>}
    <dialog className="reader-dialog" ref={dialog} onClose={() => setSelected(null)}><div className="reader-dialog-heading"><h2>নিজের নোট</h2><button className="button button-quiet" onClick={close}>বন্ধ করুন</button></div>
      {detail.isPending && selected && <p role="status">নোট পাওয়া হচ্ছে…</p>}{detail.isError && <p className="notice" role="alert">নোটটি পাওয়া যায়নি। আবার খুলে দেখুন।</p>}
      {detail.data && <AnnotationNote key={detail.data.id + detail.data.updated_at} kind={kind} annotation={detail.data} onSaved={close} />}
    </dialog>
  </section>;
}

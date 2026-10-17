"use client";

import { SiteText, SiteDiv } from "@/components/site-language";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { personalAnnotation, personalAnnotations, type AnnotationKind } from "@/api/annotations";
import type { AnnotationSummary } from "@/api/types";
import { AnnotationNote } from "./annotation-note";

export function PersonalNotes({ book }: { book?: string } = {}) {
  const [kind, setKind] = useState<AnnotationKind>("highlights");
  const [selected, setSelected] = useState<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const records = useInfiniteQuery({ queryKey: ["annotations", "personal", kind, book ?? ""], initialPageParam: "", queryFn: ({ pageParam, signal }) => personalAnnotations(kind, { cursor: pageParam, book, signal }), getNextPageParam: (page) => page.next_cursor ?? undefined });
  const detail = useQuery({ queryKey: ["annotations", "detail", kind, selected], queryFn: ({ signal }) => personalAnnotation(kind, selected!, signal), enabled: selected !== null });
  const close = () => { dialog.current?.close(); setSelected(null); };
  return <section><SiteDiv className="annotation-actions" role="group" aria-label="নোটের ধরন"><button className="button button-quiet" aria-pressed={kind === "highlights"} onClick={() => setKind("highlights")}><SiteText>{"দাগ ও উদ্ধৃতি"}</SiteText></button>
    <button className="button button-quiet" aria-pressed={kind === "bookmarks"} onClick={() => setKind("bookmarks")}><SiteText>{"বুকমার্ক"}</SiteText></button></SiteDiv>
    {records.isPending && <p role="status"><SiteText>{"নোট পাওয়া হচ্ছে…"}</SiteText></p>}
    {records.isError && <p className="notice" role="alert"><SiteText>{"নোট পাওয়া যায়নি। "}</SiteText><button className="button button-quiet" onClick={() => void records.refetch()}><SiteText>{"আবার চেষ্টা করুন"}</SiteText></button></p>}
    <div className="annotation-list">{records.data?.pages.flatMap<AnnotationSummary>((page) => page.entries).map((annotation) => <button className="annotation-card" data-annotation-id={annotation.id} key={annotation.id} onClick={() => { setSelected(annotation.id); dialog.current?.showModal(); }}>
      <strong>{annotation.book_title}</strong><span>{annotation.chapter_label}</span><span>{"text_preview" in annotation ? annotation.text_preview : annotation.preview_text}</span><span>{annotation.note_preview}</span><span className="text-link"><SiteText>{"নোট খুলুন →"}</SiteText></span>
    </button>)}</div>
    {records.data && records.data.pages[0].entries.length === 0 && <p className="empty-state"><SiteText>{"এখনও কোনো "}</SiteText>{kind === "bookmarks" ? <SiteText>{"বুকমার্ক"}</SiteText> : <SiteText>{"দাগ বা উদ্ধৃতি"}</SiteText>}<SiteText>{" নেই। বই পড়ার সময় এগুলো তৈরি করতে পারবেন।"}</SiteText></p>}
    {records.hasNextPage && <button className="button button-quiet" disabled={records.isFetchingNextPage} onClick={() => void records.fetchNextPage()}><SiteText>{"আরও দেখুন"}</SiteText></button>}
    <dialog className="reader-dialog" ref={dialog} onClose={() => setSelected(null)}><div className="reader-dialog-heading"><h2><SiteText>{"নিজের নোট"}</SiteText></h2><button className="button button-quiet" onClick={close}><SiteText>{"বন্ধ করুন"}</SiteText></button></div>
      {detail.isPending && selected && <p role="status"><SiteText>{"নোট পাওয়া হচ্ছে…"}</SiteText></p>}{detail.isError && <p className="notice" role="alert"><SiteText>{"নোটটি পাওয়া যায়নি। আবার খুলে দেখুন।"}</SiteText></p>}
      {detail.data && <AnnotationNote key={detail.data.id + detail.data.updated_at} kind={kind} annotation={detail.data} onSaved={close} />}
    </dialog>
  </section>;
}

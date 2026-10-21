"use client";

import Link from "next/link";
import { Icon } from "./icon";
import { annotationColors, annotationViews, annotationViewEnglish } from "@/lib/annotation-options";
import { useDebouncedQuery } from "@/lib/debounced-query";
import { SiteText, SiteDiv, useSiteLanguage } from "@/components/site-language";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useId, useRef, useState } from "react";
import { personalAnnotation, personalAnnotations, type AnnotationKind } from "@/api/annotations";
import type { AnnotationSummary } from "@/api/types";
import { AnnotationNote } from "./annotation-note";
import { AnnotationReaderAction } from "./annotation-reader-action";

export function PersonalNotes({ book }: { book?: string } = {}) {
  const { t, number, language } = useSiteLanguage(), searchId = useId();
  const [view, setView] = useState<keyof typeof annotationViews>("notes");
  const kind: AnnotationKind = view === "bookmarks" ? "bookmarks" : "highlights";
  const [query, setQuery] = useState("");
  const [color, setColor] = useState("");
  const debounced = useDebouncedQuery(query);
  const [selected, setSelected] = useState<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const records = useInfiniteQuery({ queryKey: ["annotations", "personal", kind, book ?? "", view, debounced, color], initialPageParam: "", queryFn: ({ pageParam, signal }) => personalAnnotations(kind, { cursor: pageParam, includeCounts: !pageParam, book, view: view === "bookmarks" ? "all" : view, q: debounced, color: view === "bookmarks" ? "" : color, signal }), getNextPageParam: (page) => page.next_cursor ?? undefined });
  const detail = useQuery({ queryKey: ["annotations", "detail", kind, selected], queryFn: ({ signal }) => personalAnnotation(kind, selected!, signal), enabled: selected !== null });
  const close = () => { dialog.current?.close(); setSelected(null); };
  const groups = new Map<string, { title: string; entries: AnnotationSummary[] }>();
  for (const annotation of records.data?.pages.flatMap<AnnotationSummary>((page) => page.entries) ?? []) {
    const group = groups.get(annotation.book_slug) ?? { title: annotation.book_title, entries: [] };
    group.entries.push(annotation); groups.set(annotation.book_slug, group);
  }
  return <section className="personal-notes"><SiteDiv className="annotation-actions notes-view-tabs" role="group" aria-label="নোটের ধরন">{Object.entries(annotationViews).map(([value, label]) => <button key={value} className="button button-quiet" aria-pressed={view === value} onClick={() => setView(value as keyof typeof annotationViews)}><Icon name={value === "bookmarks" ? "bookmark" : value === "highlights" ? "edit" : "notes"} />{language === "en" ? annotationViewEnglish[value as keyof typeof annotationViews] : label}{records.data?.pages[0].counts && <span className="count-badge">{number(records.data.pages[0].counts[value as keyof typeof annotationViews])}</span>}</button>)}</SiteDiv>
    <div className="notes-toolbar"><label className="notes-search"><Icon name="search" /><span className="visually-hidden"><SiteText>নোট খুঁজুন</SiteText></span><input id={searchId} type="search" maxLength={120} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("নোট খুঁজুন")} /></label>{view !== "bookmarks" && <label className="notes-color"><span className="visually-hidden"><SiteText>রং</SiteText></span><select aria-label={t("রং")} value={color} onChange={(event) => setColor(event.target.value)}><option value=""><SiteText>সব রং</SiteText></option>{Object.entries(annotationColors).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></label>}</div>
    {records.isPending && <p role="status"><SiteText>{"নোট পাওয়া হচ্ছে…"}</SiteText></p>}
    {records.isError && <p className="notice" role="alert"><SiteText>{"নোট পাওয়া যায়নি। "}</SiteText><button className="button button-quiet" onClick={() => void records.refetch()}><SiteText>{"আবার চেষ্টা করুন"}</SiteText></button></p>}
    {[...groups].map(([slug, group]) => <section key={slug} className="notes-book-group"><h2><Link href={`/books/${slug}/`}>{group.title}</Link></h2><div className="annotation-list">{group.entries.map((annotation) => <div key={annotation.id}><button className="annotation-card" data-annotation-id={annotation.id} data-color={"color" in annotation ? annotation.color : undefined} onClick={() => { setSelected(annotation.id); dialog.current?.showModal(); }}>
      <span className="annotation-chapter">{annotation.chapter_label}</span><span className="annotation-quote">{"text_preview" in annotation ? annotation.text_preview : annotation.preview_text}</span><span className="annotation-note-preview">{annotation.note_preview}</span><span className="text-link"><Icon name="notes" /><SiteText>{"নোট খুলুন →"}</SiteText></span>
    </button><AnnotationReaderAction kind={kind} identifier={annotation.id} /></div>)}</div></section>)}
    {records.data && records.data.pages[0].entries.length === 0 && <div className="empty-state"><Icon name={kind === "bookmarks" ? "bookmark" : "notes"} size={28} /><h2><SiteText>{query || color && view !== "bookmarks" ? "কোনো নোট মেলেনি" : { notes: "এখনও কোনো নোট নেই", highlights: "এখনও কোনো দাগ নেই", quotes: "এখনও কোনো উদ্ধৃতি নেই", bookmarks: "এখনও কোনো বুকমার্ক নেই" }[view]}</SiteText></h2><p><SiteText>{query || color && view !== "bookmarks" ? "ফিল্টার বদলে আবার খুঁজুন।" : "পড়ার সময় লেখা নির্বাচন করে নোট রাখুন।"}</SiteText></p>{(query || color && view !== "bookmarks") && <button className="button button-quiet" onClick={() => { setQuery(""); setColor(""); }}><SiteText>ফিল্টার সরান</SiteText></button>}</div>}
    {records.hasNextPage && <button className="button button-quiet" disabled={records.isFetchingNextPage} onClick={() => void records.fetchNextPage()}><SiteText>{"আরও দেখুন"}</SiteText></button>}
    <dialog className="reader-dialog" ref={dialog} onClose={() => setSelected(null)}><div className="reader-dialog-heading"><h2><SiteText>{"নিজের নোট"}</SiteText></h2><button className="button button-quiet" onClick={close}><SiteText>{"বন্ধ করুন"}</SiteText></button></div>
      {detail.isPending && selected && <p role="status"><SiteText>{"নোট পাওয়া হচ্ছে…"}</SiteText></p>}{detail.isError && <p className="notice" role="alert"><SiteText>{"নোটটি পাওয়া যায়নি। আবার খুলে দেখুন।"}</SiteText></p>}
      {detail.data && <AnnotationNote key={detail.data.id + detail.data.updated_at} kind={kind} annotation={detail.data} onSaved={close} />}
    </dialog>
  </section>;
}

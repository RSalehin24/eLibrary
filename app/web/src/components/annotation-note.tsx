"use client";

import { SiteText } from "@/components/site-language";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { deleteAnnotation, updateNote, type AnnotationKind } from "@/api/annotations";
import { APIError } from "@/api/http";
import type { Bookmark, Highlight } from "@/api/types";
import { useUnsavedChanges } from "@/lib/unsaved-changes";
import { useUpdateParticipant } from "@/lib/update-safety";

export function AnnotationNote({ annotation, kind, onSaved }: { annotation: Bookmark | Highlight; kind: AnnotationKind; onSaved: () => void }) {
  const [note, setNote] = useState(annotation.note);
  const [remove, setRemove] = useState(false);
  const queries = useQueryClient();
  useUnsavedChanges(note !== annotation.note);
  const refreshed = async () => { await queries.invalidateQueries({ queryKey: ["annotations"] }); onSaved(); };
  const saving = useMutation({ mutationFn: () => updateNote(kind, { id: annotation.id, note, expected_updated_at: annotation.updated_at }), onSuccess: refreshed, retry: false });
  const deleting = useMutation({ mutationFn: () => deleteAnnotation(kind, annotation.id), onSuccess: refreshed, retry: false });
  useUpdateParticipant({ dirty: saving.isPending || deleting.isPending });
  const failed = saving.error ?? deleting.error;
  return <section className="annotation-note"><p>{annotation.book_title} · {annotation.chapter_label}</p>
    {"text" in annotation && <blockquote>{annotation.text}</blockquote>}
    <form onSubmit={(event) => { event.preventDefault(); saving.mutate(); }}>
      <label htmlFor={`note-${annotation.id}`}><SiteText>{"আপনার নোট"}</SiteText></label><textarea id={`note-${annotation.id}`} rows={5} maxLength={5000} value={note} onChange={(event) => setNote(event.target.value)} />
      {failed && <p className="notice" role="alert">{failed instanceof APIError && failed.code === "state_conflict" ? <SiteText>{"নোটটি অন্য জায়গায় বদলেছে। আবার খুলে নতুন তথ্য দেখুন।"}</SiteText> : <SiteText>{"পরিবর্তন সংরক্ষণ হয়নি। আবার চেষ্টা করুন।"}</SiteText>}</p>}
      <div className="annotation-actions"><button className="button" disabled={saving.isPending || deleting.isPending}><SiteText>{"নোট সংরক্ষণ করুন"}</SiteText></button>
        <button className="button button-quiet" type="button" onClick={() => setRemove(true)}><SiteText>{"মুছে ফেলুন"}</SiteText></button></div>
    </form>
    {remove && <div className="notice"><p><SiteText>{"এই "}</SiteText>{kind === "bookmarks" ? <SiteText>{"বুকমার্ক"}</SiteText> : <SiteText>{"দাগ ও নোট"}</SiteText>}<SiteText>{" মুছে ফেলবেন?"}</SiteText></p><div className="annotation-actions">
      <button className="button" disabled={deleting.isPending || saving.isPending} onClick={() => deleting.mutate()}><SiteText>{"হ্যাঁ, মুছে ফেলুন"}</SiteText></button><button className="button button-quiet" onClick={() => setRemove(false)}><SiteText>{"ফিরে যান"}</SiteText></button>
    </div></div>}
  </section>;
}

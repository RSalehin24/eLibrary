"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createHighlight } from "@/api/annotations";
import type { HighlightInput, ReaderSession } from "@/api/types";
import type { TextSelection } from "@/lib/reader-annotations";
import { useUnsavedChanges } from "@/lib/unsaved-changes";
import { useUpdateParticipant } from "@/lib/update-safety";

export function HighlightForm({ context, selection, onSaved }: { context: { session: ReaderSession; chapter: number }; selection: TextSelection; onSaved: () => void }) {
  const [note, setNote] = useState("");
  const [color, setColor] = useState<HighlightInput["color"]>("yellow");
  const [kind, setKind] = useState<HighlightInput["kind"]>("highlight");
  const queries = useQueryClient();
  useUnsavedChanges(true);
  const chapter = context.session.chapters[context.chapter];
  const saving = useMutation({ mutationFn: () => createHighlight(context.session.id, { text: selection.text, selector: selection.selector, chapter_href: chapter.path, chapter_label: chapter.label, note, color, kind }), retry: false,
    onSuccess: async () => { await queries.invalidateQueries({ queryKey: ["annotations"] }); onSaved(); } });
  useUpdateParticipant({ dirty: saving.isPending });
  return <form className="highlight-form" onSubmit={(event) => { event.preventDefault(); saving.mutate(); }}><blockquote>{selection.text}</blockquote>
    <label htmlFor="highlight-kind">কীভাবে রাখবেন</label><select id="highlight-kind" value={kind} onChange={(event) => setKind(event.target.value as HighlightInput["kind"])}><option value="highlight">দাগ</option><option value="quote">উদ্ধৃতি</option></select>
    <label htmlFor="highlight-color">দাগের রং</label><select id="highlight-color" value={color} onChange={(event) => setColor(event.target.value as HighlightInput["color"])}>
      <option value="yellow">হলুদ</option><option value="green">সবুজ</option><option value="blue">নীল</option><option value="pink">গোলাপি</option><option value="underline">নিচে রেখা</option></select>
    <label htmlFor="highlight-note">আপনার নোট</label><textarea id="highlight-note" rows={4} maxLength={5000} value={note} onChange={(event) => setNote(event.target.value)} />
    {saving.isError && <p className="notice" role="alert">সংরক্ষণ হয়নি। ফল অনিশ্চিত হলে নিজের নোটে দেখে তারপর আবার চেষ্টা করুন।</p>}
    <button className="button" disabled={saving.isPending}>দাগ ও নোট সংরক্ষণ করুন</button>
  </form>;
}

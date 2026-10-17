"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { readBookControls } from "@/api/book-lifecycle";
import { reloadManagedForm } from "@/lib/managed-form";
import type { BookEditor } from "@/lib/book-editor";
import { AdminDialog } from "./admin-dialog";
import { AccountFeedback } from "./account-feedback";
import { AdminText } from "./admin-language";

const problemLabels = { paper_book: "কাগজের বইয়ের ফাইল আবার তৈরি করা যায় না।", processing_access_required: "বই আবার তৈরি করতে প্রসেসিংয়ের অনুমতি প্রয়োজন।", unfinished_work: "চলমান কাজ শেষ বা বাতিল করে আবার চেষ্টা করুন।", source_unavailable: "এই বইয়ের জন্য নির্ধারিত ওয়েবসাইটের উৎস পাওয়া যায়নি। EPUB আপলোড করতে পারবেন।" };

export function BookLifecycleControls({ editor }: { editor: BookEditor }) {
  const { book, dirty, pending, regenerate, remove } = editor;
  const regenerateDialog = useRef<HTMLDialogElement>(null), removeDialog = useRef<HTMLDialogElement>(null);
  const controls = useQuery({ queryKey: ["private", "book-controls", book.slug], queryFn: ({ signal }) => readBookControls(book.slug, signal), refetchInterval: 5000, refetchIntervalInBackground: false });
  const changed = controls.data && controls.data.book_revision !== book.updated_at;
  const blocked = pending || dirty || !!changed || !!regenerate.error || !!remove.error;
  const operation = regenerate.data?.operation_id ?? controls.data?.active_operation_id;
  return <section className="book-lifecycle-controls"><h2><AdminText>বইয়ের কাজ</AdminText></h2><div className="account-actions">
    {book.record_type !== "manual" && <AdminDialog title="বই আবার তৈরি করবেন?" trigger="বই আবার তৈরি করুন" icon="refresh" dialogRef={regenerateDialog} disabled={blocked || !controls.data?.can_regenerate}>
      <p>{book.title}</p><p><AdminText>ওয়েবসাইট থেকে নতুন করে লেখা এনে HTML ও EPUB তৈরি হবে। আগের ফাইল ও পাঠকের নোট সংরক্ষিত থাকবে। প্রকাশের আগে আবার পর্যালোচনা করতে হবে।</AdminText></p>
      <button className="button" disabled={blocked || !controls.data?.can_regenerate} onClick={() => { regenerateDialog.current?.close(); regenerate.mutate(crypto.randomUUID()); }}><AdminText>আবার তৈরি শুরু করুন</AdminText></button>
    </AdminDialog>}
    <AdminDialog title="বইটি সরাবেন?" trigger="বই সরান" icon="trash" dialogRef={removeDialog} className="button button-danger" disabled={blocked || !controls.data?.can_remove}>
      <p>{book.title}</p><p><AdminText>বইটি পাঠাগার থেকে সরবে এবং আর খোলা যাবে না। বইয়ের রেকর্ড, ফাইল ও ব্যক্তিগত নোট সংরক্ষিত থাকবে।</AdminText></p>
      <button className="button button-danger" disabled={blocked || !controls.data?.can_remove} onClick={() => { removeDialog.current?.close(); remove.mutate(); }}><AdminText>হ্যাঁ, বইটি সরান</AdminText></button>
    </AdminDialog>
    {operation && <Link className="button button-quiet" href={`/manage/jobs/${operation}/`}><AdminText>কাজের অবস্থা দেখুন</AdminText></Link>}
  </div>
    {controls.data?.regeneration_problem && book.record_type !== "manual" && <p className="muted"><AdminText>{problemLabels[controls.data.regeneration_problem]}</AdminText></p>}
    {dirty && <p className="muted"><AdminText>আগে সম্পাদিত তথ্য সংরক্ষণ করুন।</AdminText></p>}
    {controls.isError && <p className="notice" role="alert"><AdminText>বইয়ের নিয়ন্ত্রণ পাওয়া যায়নি।</AdminText> <button className="button button-quiet" onClick={() => void controls.refetch()}><AdminText>আবার দেখুন</AdminText></button></p>}
    {regenerate.isPending && <p role="status"><AdminText>বই আবার তৈরির কাজ যোগ হচ্ছে…</AdminText></p>}
    <AccountFeedback error={regenerate.error ?? remove.error} />
    {regenerate.error && regenerate.variables && <Link className="text-link" href={`/manage/jobs/${regenerate.variables}/`}><AdminText>এই অনুরোধের ফল দেখুন</AdminText></Link>}
    {(changed || regenerate.error || remove.error) && <button className="button button-quiet" onClick={reloadManagedForm}><AdminText>বর্তমান তথ্য খুলুন</AdminText></button>}
  </section>;
}

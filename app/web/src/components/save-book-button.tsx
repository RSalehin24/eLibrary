"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { readSavedBook, saveBook } from "@/api/library";
import { useUpdateParticipant } from "@/lib/update-safety";

export function SaveBookButton({ slug }: { slug: string }) {
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const key = ["private", "saved-book", slug, session.data?.user?.id];
  const state = useQuery({ queryKey: key, queryFn: ({ signal }) => readSavedBook(slug, signal), enabled: session.data?.authenticated === true && !session.data.user?.totp_setup_required });
  const saving = useMutation({ mutationFn: (saved: boolean) => saveBook(slug, saved), retry: false, onSuccess: (updated) => { client.setQueryData(key, updated); } });
  useUpdateParticipant({ dirty: saving.isPending });
  if (!session.data?.authenticated || session.data.user?.totp_setup_required) return null;
  return <div className="book-actions"><button className="button button-quiet" disabled={!state.data || state.isFetching || saving.isPending || !!saving.error} onClick={() => saving.mutate(!state.data?.saved)}>
    {state.data?.saved ? "সংরক্ষিত তালিকা থেকে সরান" : "পরে পড়ার জন্য রাখুন"}
  </button>{(state.error || saving.error) && <p role="alert">সংরক্ষিত তালিকার অবস্থা নিশ্চিত করা যায়নি। <button type="button" className="button button-quiet" onClick={() => { saving.reset(); void state.refetch(); }}>বর্তমান অবস্থা দেখুন</button></p>}</div>;
}

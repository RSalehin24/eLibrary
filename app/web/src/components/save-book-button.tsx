"use client";

import { SiteText } from "@/components/site-language";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { readSavedBook, saveBook } from "@/api/library";
import { useUpdateParticipant } from "@/lib/update-safety";
import Link from "next/link";
import { Icon } from "./icon";

export function SaveBookButton({ slug }: { slug: string }) {
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const key = ["private", "saved-book", slug, session.data?.user?.id];
  const state = useQuery({ queryKey: key, queryFn: ({ signal }) => readSavedBook(slug, signal), enabled: session.data?.authenticated === true && !session.data.user?.totp_setup_required });
  const saving = useMutation({ mutationFn: (saved: boolean) => saveBook(slug, saved), retry: false, onSuccess: (updated) => { client.setQueryData(key, updated); } });
  useUpdateParticipant({ dirty: saving.isPending });
  if (!session.data?.authenticated || session.data.user?.totp_setup_required) return null;
  return <div className="book-save-action"><button className="button button-quiet" disabled={!state.data || state.isFetching || saving.isPending || !!saving.error} onClick={() => saving.mutate(!state.data?.saved)}>
    <Icon name={state.data?.saved ? "bookmark" : "plus"} />{state.data?.saved ? <SiteText>{"আমার বই থেকে সরান"}</SiteText> : <SiteText>{"আমার বইয়ে যোগ করুন"}</SiteText>}
  </button>{state.data?.saved && <Link className="button button-quiet" href="/my-books/"><Icon name="read" /><SiteText>{"আমার বই দেখুন"}</SiteText></Link>}
    {(state.error || saving.error) && <p role="alert"><SiteText>{"সংরক্ষিত তালিকার অবস্থা নিশ্চিত করা যায়নি। "}</SiteText><button type="button" className="button button-quiet" onClick={() => { saving.reset(); void state.refetch(); }}><SiteText>{"বর্তমান অবস্থা দেখুন"}</SiteText></button></p>}</div>;
}

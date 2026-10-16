"use client";

import Link from "next/link";
import { useInfiniteQuery } from "@tanstack/react-query";
import { kindleHistory } from "@/api/kindle";
import type { KindleCollection } from "@/api/types";
import { jobPollingInterval } from "@/lib/job-status";
import { KindleSummary } from "./kindle-summary";

export function KindleHistory({ initial }: { initial: KindleCollection }) {
  const history = useInfiniteQuery({ queryKey: ["private", "kindle", "history"], initialPageParam: "", queryFn: ({ signal, pageParam }) => kindleHistory(pageParam, signal), initialData: { pages: [initial], pageParams: [""] }, getNextPageParam: (page) => page.next_cursor ?? undefined,
    refetchInterval: (query) => jobPollingInterval(query.state.data?.pages.flatMap((page) => page.entries) ?? [], query.state.fetchFailureCount), refetchIntervalInBackground: false });
  const entries = history.data.pages.flatMap((page) => page.entries);
  return <>{history.isError && <p className="field-error" role="alert">হালনাগাদ অবস্থা পাওয়া যায়নি। <button className="button button-quiet" onClick={() => void history.refetch()}>আবার দেখুন</button></p>}
    <ul className="job-list">{entries.map((operation) => <li className="job-card" key={operation.id}><KindleSummary operation={operation} /><Link className="text-link" href={`/kindle/operations/${operation.id}/`}>এই অনুরোধের বিস্তারিত →</Link></li>)}</ul>
    {!entries.length && <p className="empty-state">এখনও কোনো কিন্ডল অনুরোধ নেই। <Link className="text-link" href="/my-books/">নিজের বই দেখুন →</Link></p>}
    {history.hasNextPage && <button className="button button-quiet" disabled={history.isFetchingNextPage} onClick={() => void history.fetchNextPage()}>আরও অনুরোধ দেখুন</button>}</>;
}

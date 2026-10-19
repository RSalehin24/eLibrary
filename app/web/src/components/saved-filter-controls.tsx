"use client";

import Link from "next/link";
import { useId, useRef, useState } from "react";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { createSavedFilter, deleteSavedFilter, readSavedFilters } from "@/api/saved-filters";
import type { SavedFilter } from "@/api/types";
import { APIError } from "@/api/http";
import { AccountFeedback } from "./account-feedback";
import { Icon } from "./icon";
import { SiteText, useSiteLanguage } from "./site-language";

export function SavedFilterControls({ target, values, href }: { target: SavedFilter["target"]; values: Record<string, string>; href: (parameters: Record<string, unknown>) => string | null }) {
  const { t } = useSiteLanguage(), id = useId(), client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const [name, setName] = useState("");
  const command = useRef({ signature: "", identifier: "" });
  const key = ["private", "saved-filters", session.data?.user?.id, target];
  const saved = useInfiniteQuery({ queryKey: key, initialPageParam: 1, enabled: !!session.data?.authenticated, queryFn: ({ pageParam, signal }) => readSavedFilters(target, pageParam, signal), getNextPageParam: (page) => page.pagination.page * page.pagination.limit < page.pagination.total_count ? page.pagination.page + 1 : undefined });
  const refresh = () => client.invalidateQueries({ queryKey: key });
  const saving = useMutation({ mutationFn: createSavedFilter, retry: false, onSuccess: () => { setName(""); void refresh(); } });
  const removing = useMutation({ mutationFn: deleteSavedFilter, retry: false, onSuccess: refresh });
  if (!session.data?.authenticated) return null;
  const entries = saved.data?.pages.flatMap((page) => page.entries) ?? [];
  return <section className="saved-catalog-filters" aria-label={t("সংরক্ষিত ফিল্টার")}>
    {saved.isError && <p role="alert"><SiteText>সংরক্ষিত ফিল্টার পাওয়া যায়নি।</SiteText> <button className="button button-quiet" onClick={() => void saved.refetch()}><SiteText>আবার চেষ্টা করুন</SiteText></button></p>}
    {entries.length > 0 && <><strong><SiteText>সংরক্ষিত ফিল্টার</SiteText></strong><ul className="saved-filter-list">{entries.map((entry) => {
      const destination = href(entry.params as Record<string, unknown>);
      return <li key={entry.id}>{destination ? <Link href={destination}><Icon name="bookmark" />{entry.name}</Link> : <span title={t("এই ফিল্টারের কিছু শর্ত এখন ব্যবহার করা যাচ্ছে না।")}>{entry.name}</span>}
        <button type="button" className="button button-quiet" aria-label={`${entry.name}: ${t("ফিল্টার মুছুন")}`} disabled={removing.isPending} onClick={() => removing.mutate(entry.id)}><Icon name="trash" /></button></li>;
    })}</ul></>}
    {saved.hasNextPage && <button type="button" className="button button-quiet" disabled={saved.isFetchingNextPage} onClick={() => void saved.fetchNextPage()}><SiteText>আরও দেখুন</SiteText></button>}
    <details className="saved-filter-create"><summary><Icon name="save" /><SiteText>এই ফিল্টার সংরক্ষণ করুন</SiteText></summary><form onSubmit={(event) => {
      event.preventDefault(); const signature = JSON.stringify([name.trim(), values]);
      if (command.current.signature !== signature) command.current = { signature, identifier: crypto.randomUUID() };
      saving.mutate({ operation_id: command.current.identifier, target, name: name.trim(), params: { ...values } });
    }}><label htmlFor={id}><SiteText>ফিল্টারের নাম</SiteText></label><div className="search-row"><input id={id} value={name} maxLength={120} required onChange={(event) => setName(event.target.value)} disabled={saving.isPending} aria-invalid={saving.error instanceof APIError && !!saving.error.fieldErrors.name} /><button className="button" disabled={saving.isPending}><SiteText>সংরক্ষণ করুন</SiteText></button></div>
      <AccountFeedback error={saving.error} conflictMessage="এই নামে আগে থেকেই একটি ফিল্টার আছে। অন্য নাম দিন।" />
      {saving.isSuccess && <p role="status"><SiteText>ফিল্টার সংরক্ষিত হয়েছে।</SiteText></p>}
    </form></details><AccountFeedback error={removing.error} />
  </section>;
}

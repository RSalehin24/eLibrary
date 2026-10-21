"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { readMetadataHistory } from "@/api/metadata-history";
import { metadataActorFallback, metadataSourceLabel } from "@/lib/metadata-history";
import { AdminDate, AdminText } from "./admin-language";
import { Icon } from "./icon";
import { NumberedPagination } from "./numbered-pagination";

export function BookMetadataHistory({ slug, revision }: { slug: string; revision: string }) {
  const [page, setPage] = useState(1);
  const history = useQuery({ queryKey: ["private", "metadata-history", slug, revision, page],
    queryFn: ({ signal }) => readMetadataHistory(slug, page, signal) });
  const pagination = history.data?.pagination;
  return <section className="account-section" id="metadata-history" aria-labelledby="metadata-history-heading">
    <h2 id="metadata-history-heading"><Icon name="notes" /> <AdminText>{"তথ্যের ইতিহাস"}</AdminText></h2>
    <p className="muted"><AdminText>{"বইয়ের তথ্য কখন, কীভাবে এবং কে পরিবর্তন করেছেন তা এখানে পাবেন।"}</AdminText></p>
    {history.isPending && <p role="status"><AdminText>{"তথ্যের ইতিহাস খোলা হচ্ছে…"}</AdminText></p>}
    {history.isError && <p className="field-error" role="alert"><AdminText>{"তথ্যের ইতিহাস পাওয়া যায়নি।"}</AdminText>{" "}<button className="button button-quiet" type="button" onClick={() => void history.refetch()}><Icon name="refresh" /><AdminText>{"আবার দেখুন"}</AdminText></button></p>}
    {pagination?.total_count === 0 && <p><AdminText>{"এখনও কোনো পরিবর্তন সংরক্ষিত হয়নি।"}</AdminText></p>}
    <ol className="job-list">{history.data?.entries.map((version) => <li className="job-card" key={version.id}>
      <strong><AdminText>{metadataSourceLabel(version.source)}</AdminText></strong>
      <p><AdminDate value={version.created_at} /> · {version.created_by ? version.created_by.name || <AdminText>{"নাম সংরক্ষিত নেই"}</AdminText> : <AdminText>{metadataActorFallback(version.source)}</AdminText>}</p>
      <p>{version.notes || <AdminText>{"পরিবর্তনের কারণ লেখা হয়নি।"}</AdminText>}</p>
    </li>)}</ol>
    {pagination && <NumberedPagination page={page} totalPages={Math.max(1, Math.ceil(pagination.total_count / pagination.limit))} onPageChange={setPage} busy={history.isFetching} label="তথ্যের ইতিহাসের পাতা" />}
  </section>;
}

"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { readManagementOverview, readOverviewWork } from "@/api/overview";
import type { ManagementOverview, OverviewWork } from "@/api/types";
import { activityPollingInterval, jobTimestamp } from "@/lib/job-status";
import { useAdminLanguage } from "./admin-language";
import { OverviewWorkGroup } from "./overview-work";

function workIsActive(work: OverviewWork | undefined) {
  return [work?.processing, work?.account_mail].some((group) => group && group.counts.queued + group.counts.running + group.counts.retry_wait > 0);
}

export function ManagementOverviewWorkspace({ initial }: { initial: ManagementOverview }) {
  const { t, language, number } = useAdminLanguage();
  const snapshot = useQuery({ queryKey: ["private", "overview", "summary"], queryFn: ({ signal }) => readManagementOverview(signal), initialData: initial, refetchOnWindowFocus: false });
  const work = useQuery({ queryKey: ["private", "overview", "work"], queryFn: ({ signal }) => readOverviewWork(signal), initialData: initial.work,
    refetchInterval: (state) => activityPollingInterval(workIsActive(state.state.data), state.state.fetchFailureCount), refetchIntervalInBackground: false });
  const { books, sources, accounts } = snapshot.data;
  async function refresh() { await Promise.all([snapshot.refetch(), work.refetch()]); }
  return <><div className="overview-refresh"><p className="muted">{t("হালনাগাদ")}: {jobTimestamp(snapshot.data.generated_at, language)}</p>
    <button className="button button-quiet" onClick={() => void refresh()} disabled={snapshot.isFetching || work.isFetching}>{t("সব তথ্য আবার দেখুন")}</button></div>
    {(snapshot.isError || work.isError) && <p className="field-error" role="alert">{t("হালনাগাদ তথ্য পাওয়া যায়নি। প্রদর্শিত তথ্য আগের অবস্থার হতে পারে।")}</p>}
    <div className="overview-grid">
      {books && <section className="account-section"><h2>{t("আপনার পরিচালনাযোগ্য বই")}</h2>
        <dl className="book-facts">
          <div><dt>{t("মোট")}</dt><dd>{number(books.total)}</dd></div>
          {(books.draft + books.ready) > 0 && <div><dt>{t("প্রকাশের অপেক্ষায়")}</dt><dd>{number(books.draft + books.ready)}</dd></div>}
          <div><dt>{t("প্রক্রিয়াধীন")}</dt><dd>{number(books.processing)}</dd></div>
          <div><dt>{t("প্রকাশিত")}</dt><dd>{number(books.published)}</dd></div>
          <div><dt>{t("আর্কাইভে")}</dt><dd>{number(books.archived)}</dd></div>
        </dl><Link className="text-link" href="/manage/books/">{t("বই দেখুন →")}</Link></section>}
      {sources && <section className="account-section"><h2>{t("ওয়েবসাইটের বই")}</h2><dl className="book-facts"><div><dt>{t("মোট")}</dt><dd>{number(sources.total)}</dd></div><div><dt>{t("অসংযুক্ত")}</dt><dd>{number(sources.unlinked)}</dd></div><div><dt>{t("বই সংযুক্ত")}</dt><dd>{number(sources.linked)}</dd></div><div><dt>{t("সংযুক্ত বই অপসারিত")}</dt><dd>{number(sources.removed)}</dd></div></dl><Link className="text-link" href="/manage/sources/?status=unlinked">{t("অসংযুক্ত উৎস দেখুন →")}</Link></section>}
      {accounts && <section className="account-section"><h2>{t("পাঠকের হিসাব")}</h2><dl className="book-facts"><div><dt>{t("মোট")}</dt><dd>{number(accounts.total)}</dd></div><div><dt>{t("সক্রিয়")}</dt><dd>{number(accounts.active)}</dd></div><div><dt>{t("প্রথম প্রবেশের প্রস্তুতি বাকি")}</dt><dd>{number(accounts.setup_pending)}</dd></div></dl><Link className="text-link" href="/manage/users-access/?status=setup_pending">{t("প্রস্তুতি বাকি হিসাব দেখুন →")}</Link></section>}
    </div><div className="overview-grid overview-work">
      {work.data.processing && <OverviewWorkGroup title="প্রক্রিয়াকরণের কাজ" summary={work.data.processing} href="/manage/jobs/" />}
      {work.data.account_mail && <OverviewWorkGroup title="আমন্ত্রণের কাজ" summary={work.data.account_mail} href="/manage/users-access/" />}
    </div></>;
}

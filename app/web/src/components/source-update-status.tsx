import Link from "next/link";
import type { SourceEntry } from "@/api/types";
import { AdminDate, AdminText } from "./admin-language";
import { Icon } from "./icon";

export function SourceUpdateStatus({ entry }: { entry: SourceEntry }) {
  const update = entry.source_update;
  if (!entry.book || entry.book.deleted_at) return null;
  return <div className={`source-update source-update-${update?.status ?? "unknown"}`}>
    <span className="source-update-label"><Icon name={update?.status === "available" ? "refresh" : update?.status === "current" ? "check" : "schedule"} /><AdminText>{update?.status === "available" ? "আপডেট আছে" : update?.status === "current" ? "সূচিতে পরিবর্তন নেই" : "আপডেট পরীক্ষা বাকি"}</AdminText></span>
    {update && <small><AdminText>পরীক্ষা করা হয়েছে</AdminText>: <AdminDate value={update.checked_at} /></small>}
    {update?.source_complete && update.status === "available" && <span><AdminText>ওয়েবসাইটে বইটি সম্পূর্ণ হয়েছে</AdminText></span>}
    {update?.status === "available" && entry.can_edit_book && <Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(entry.book.slug)}/`}><Icon name="refresh" /><AdminText>বই আপডেট করুন</AdminText></Link>}
  </div>;
}

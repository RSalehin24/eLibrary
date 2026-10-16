import { AdminDate, AdminText } from "@/components/admin-language";
import Link from "next/link";
import type { SourceEntry } from "@/api/types";
import { sourceStatus } from "@/lib/source-status";

export function SourceSummary({ entry }: { entry: SourceEntry }) {
  return <><div className="job-heading"><h2>{entry.title}</h2><span className="status-label">{sourceStatus(entry)}</span></div>
    <p>{entry.author_line || "লেখকের তথ্য নেই"}</p><p className="muted"><AdminText>{"উৎসে শেষ দেখা: "}</AdminText><AdminDate value={entry.last_seen_at} /></p>
    {entry.book && <p><AdminText>{"সংযুক্ত বই: "}</AdminText>{entry.book.title}{entry.can_edit_book && <><br /><Link className="text-link" href={`/manage/books/${encodeURIComponent(entry.book.slug)}/`}><AdminText>{"বইয়ের তথ্য পর্যালোচনা করুন →"}</AdminText></Link></>}</p>}
  </>;
}

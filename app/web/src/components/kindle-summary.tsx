import { SiteText, SiteDate } from "@/components/site-language";
import type { KindleOperation } from "@/api/types";
import { kindleStates, recipientStates, kindleError } from "@/lib/kindle-status";

export function KindleSummary({ operation }: { operation: KindleOperation }) {
  return <><div className="job-heading"><h2>{operation.book.title}</h2><span className="status-label"><SiteText>{kindleStates[operation.state]}</SiteText></span></div>
    <p className="muted"><SiteText>{"অনুরোধ: "}</SiteText><SiteDate value={operation.created_at} /></p>
    <p className="muted"><SiteText>{"সর্বশেষ অবস্থা: "}</SiteText><SiteDate value={operation.updated_at} /></p>
    {operation.requested_action === "cancel" && <p className="notice"><SiteText>{"বাতিলের অনুরোধ পাঠানো হয়েছে। কাজ থামার ফল এখনও নিশ্চিত হয়নি।"}</SiteText></p>}
    {operation.error_code && <p className="notice"><SiteText>{kindleError(operation.error_code)}</SiteText></p>}
    <ul className="kindle-recipients">{operation.recipients.map((recipient) => <li key={recipient.address}><span className="kindle-address" lang="en">{recipient.address}</span><span><SiteText>{recipientStates[recipient.outcome]}</SiteText></span></li>)}</ul>
    </>;
}

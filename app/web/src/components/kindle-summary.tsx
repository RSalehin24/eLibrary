import type { KindleOperation } from "@/api/types";
import { kindleStates, recipientStates, kindleError } from "@/lib/kindle-status";
import { jobTimestamp } from "@/lib/job-status";

export function KindleSummary({ operation }: { operation: KindleOperation }) {
  return <><div className="job-heading"><h2>{operation.book.title}</h2><span className="status-label">{kindleStates[operation.state]}</span></div>
    <p className="muted">অনুরোধ: {jobTimestamp(operation.created_at)}</p>
    {operation.requested_action === "cancel" && <p className="notice">বাতিলের অনুরোধ পাঠানো হয়েছে। কাজ থামার ফল এখনও নিশ্চিত হয়নি।</p>}
    {operation.error_code && <p className="notice">{kindleError(operation.error_code)}</p>}
    <ul className="kindle-recipients">{operation.recipients.map((recipient) => <li key={recipient.address}><span className="kindle-address" lang="en">{recipient.address}</span><span>{recipientStates[recipient.outcome]}</span></li>)}</ul>
    </>;
}

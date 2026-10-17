
import { AdminDate, AdminNumber, AdminText } from "@/components/admin-language";
import type { BackgroundJobDetail } from "@/api/types";
import { jobStage } from "@/lib/job-status";

export function JobFacts({ job }: { job: BackgroundJobDetail }) {
  return <dl className="book-facts"><div><dt><AdminText>{"কাজের পরিচয়"}</AdminText></dt><dd className="job-identifier">{job.id}</dd></div><div><dt><AdminText>{"চেষ্টা"}</AdminText></dt><dd><AdminNumber value={job.attempt_count} /></dd></div>
    <div><dt><AdminText>{"সংরক্ষিত অবস্থান"}</AdminText></dt><dd><AdminText>{job.checkpoint_saved ? "পাওয়া গেছে" : "এখনও নেই"}</AdminText></dd></div><div><dt><AdminText>{"সর্বশেষ সাড়া"}</AdminText></dt><dd><AdminDate value={job.heartbeat_at} /></dd></div>
    <div><dt><AdminText>{"নির্ধারিত সময়"}</AdminText></dt><dd><AdminDate value={job.available_at} /></dd></div><div><dt><AdminText>{"শেষ হওয়ার সময়"}</AdminText></dt><dd><AdminDate value={job.finished_at} /></dd></div></dl>;
}

export function JobAttempts({ job }: { job: BackgroundJobDetail }) {
  return <><h2><AdminText>{"সর্বশেষ চেষ্টাগুলো"}</AdminText></h2><ol className="job-list">{job.attempts.map((attempt) => <li className="job-card" key={attempt.id}><strong><AdminText>{"চেষ্টা "}</AdminText><AdminNumber value={attempt.number} /> · <AdminText>{jobStage(attempt.stage)}</AdminText></strong>
    <p className="muted"><AdminDate value={attempt.created_at} /><AdminText>{" · শেষ: "}</AdminText><AdminDate value={attempt.finished_at} /></p>{attempt.error_code && <p className="field-error"><code>{attempt.error_code}</code></p>}</li>)}</ol>
    {!job.attempts.length && <p className="muted"><AdminText>{"কাজটি এখনও শুরু হয়নি।"}</AdminText></p>}</>;
}

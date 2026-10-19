import type { BackgroundJobDetail } from "@/api/types";
import { AdminDate, AdminNumber, AdminText, useAdminLanguage } from "./admin-language";
import { jobErrorMessage } from "@/lib/job-errors";
import { Icon } from "./icon";

const steps = ["তালিকায় আছে", "লেখা সংগ্রহ", "HTML ও EPUB তৈরি", "পড়ার ফাইল প্রস্তুত", "প্রকাশিত"];
const stageSteps: Readonly<Record<string, number>> = {
  claimed: 1, fetching_source: 1, source_curated: 2, generating_exports: 2,
  collection_checkpointed: 1, source_assets_staged: 3, source_exports_generated: 3, publishing_source_assets: 3, preparing: 3,
  source_prepared: 4, publishing_source: 4, source_published: 4,
};

export function JobProgress({ job }: { job: BackgroundJobDetail }) {
  const { t } = useAdminLanguage();
  if (job.kind !== "process_source") return null;
  const current = job.state === "succeeded" ? 4 : job.state === "queued" || job.state === "retry_wait" ? 0 : stageSteps[job.stage ?? ""] ?? 1;
  return <section className="job-progress" aria-label={t("বই তৈরির অগ্রগতি")}>
    <ol className="job-steps">{steps.map((label, index) => <li key={label} className={index < current || job.state === "succeeded" ? "complete" : index === current ? "current" : ""} aria-current={index === current ? "step" : undefined}>
      <span className="job-step-number">{index < current || job.state === "succeeded" ? <Icon name="check" /> : <AdminNumber value={index + 1} />}</span><span><AdminText>{label}</AdminText></span>
    </li>)}</ol>
    {job.state === "retry_wait" ? <div className="job-next-step" role="status"><Icon name="schedule" size={24} /><div><h3><AdminText>{job.error_code === "source_content_unavailable" ? "ওয়েবসাইটে লেখা আসার অপেক্ষা" : "আবার পরীক্ষা হবে"}</AdminText></h3><p>{t(jobErrorMessage(job.error_code))}</p><p><AdminText>আবার পরীক্ষা হবে</AdminText>: <AdminDate value={job.available_at} /></p></div></div> : job.state === "queued" && <div className="job-next-step" role="status"><Icon name="schedule" size={24} /><div><h3><AdminText>নিজে থেকেই কাজ শুরু হবে</AdminText></h3>
      <p><AdminText>আগের বইগুলোর কাজ শেষ হলে এই বই তৈরি হবে। এই পাতা খোলা রাখার প্রয়োজন নেই।</AdminText></p>
      {job.queue_ahead !== null && <p><AdminText>আগে অপেক্ষায় থাকা বই</AdminText>: <strong><AdminNumber value={job.queue_ahead} /></strong></p>}
    </div></div>}
    {job.state === "running" && <p className="job-next-step" role="status"><Icon name="refresh" /><AdminText>বই তৈরি হচ্ছে। লেখা, ফাইল ও রিডারের যাচাই শেষ হলে বই প্রকাশিত হবে।</AdminText></p>}
    {job.state === "succeeded" && <p className="job-next-step" role="status"><Icon name="check" /><AdminText>বই তৈরি ও প্রকাশ সম্পন্ন হয়েছে। বই খুলে পড়তে বা ফাইল নামাতে পারবেন।</AdminText></p>}
  </section>;
}

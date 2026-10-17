import { AdminNumber, AdminText } from "./admin-language";
import type { SourceIssue } from "@/api/types";
import { Icon } from "./icon";

export function SourceVerification({ verification }: { verification: SourceIssue["verification"] }) {
  if (!verification) return null;
  return <section className={`source-verification ${verification.verified ? "verification-passed" : "notice"}`}>
    <h2><Icon name={verification.verified ? "check" : "warning"} /><AdminText>{verification.verified ? "ওয়েবসাইটের সঙ্গে স্বয়ংক্রিয় যাচাই সম্পন্ন" : "স্বয়ংক্রিয় যাচাই সম্পূর্ণ হয়নি"}</AdminText></h2>
    <p><AdminText>{"সংগৃহীত পাতা"}</AdminText>: <AdminNumber value={verification.fetched_pages} /> / <AdminNumber value={verification.source_pages} />
      {verification.expected_chapters > 0 && <> · <AdminText>{"সংগৃহীত অধ্যায়"}</AdminText>: <AdminNumber value={verification.collected_chapters} /> / <AdminNumber value={verification.expected_chapters} /></>}</p>
    <p className="muted"><AdminText>{verification.verified ? "সংগ্রহের সময় ওয়েবসাইটে থাকা অধ্যায় ও লেখার সঙ্গে মিলিয়ে যাচাই করা হয়েছে। HTML ও EPUB-এর লেখা মিললে এবং রিডার প্রস্তুত হলে বইটি নিজে থেকেই প্রকাশিত হবে।" : "সংগ্রহ বা ফাইল তৈরির সমস্যা ধরা পড়েছে। প্রসেসিংয়ের কাজ থেকে আবার চেষ্টা করা যাবে।"}</AdminText></p>
  </section>;
}

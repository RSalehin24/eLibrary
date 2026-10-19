const sourceLabels: Readonly<Record<string, string>> = {
  editorial: "বইয়ের তথ্য সম্পাদনা",
  "editorial-relationships": "লেখক, বিভাগ ও সংস্করণ সম্পাদনা",
  manual: "নিজে যোগ করা বই",
  manual_edit_before: "সম্পাদনার আগের তথ্য",
  manual_edit_after: "সম্পাদনার পরের তথ্য",
  scrape: "ওয়েবসাইট থেকে সংগ্রহ",
  curated: "ওয়েবসাইট থেকে বই তৈরি",
  before_regeneration: "নতুন সংস্করণের আগের তথ্য",
  regeneration: "ওয়েবসাইট থেকে নতুন সংস্করণ",
};

export function metadataSourceLabel(source: string) {
  return Object.hasOwn(sourceLabels, source) ? sourceLabels[source] : "বইয়ের তথ্য সংরক্ষণ";
}

export function metadataActorFallback(source: string) {
  return ["scrape", "curated", "before_regeneration", "regeneration"].includes(source) ? "স্বয়ংক্রিয়ভাবে সংরক্ষিত" : "সম্পাদকের তথ্য নেই";
}

export function jobErrorMessage(code: string) {
  const messages: Record<string, string> = {
    source_url_not_allowed: "বইয়ের লিংকটি নির্ধারিত ওয়েবসাইটের নয়। লিংক ও ওয়েবসাইটের সেটিংস পরীক্ষা করুন।",
    mail_acceptance_unknown: "ইমেইল সার্ভার বার্তাটি গ্রহণ করেছে কি না নিশ্চিত নয়। আবার পাঠানোর আগে যাচাই করুন।",
    source_duplicate: "একই নামে আরেকটি বই পাওয়া গেছে। বই দুটি মিলিয়ে সিদ্ধান্ত নিন।",
    source_incomplete: "বইয়ের সব লেখা পাওয়া যায়নি। সংগ্রহের ফল পরীক্ষা করুন।",
  };
  return messages[code] ?? "কাজটি শেষ করা যায়নি। বিস্তারিত খুলে সমস্যাটি দেখুন।";
}

export function waitDuration(seconds: number) {
  const units = [{ size: 86400, label: "দিন" }, { size: 3600, label: "ঘণ্টা" }, { size: 60, label: "মিনিট" }];
  const unit = units.find((candidate) => seconds >= candidate.size);
  return unit ? { value: Math.floor(seconds / unit.size), label: unit.label } : { value: seconds, label: "সেকেন্ড" };
}

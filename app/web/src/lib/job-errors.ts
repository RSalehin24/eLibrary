export function jobErrorMessage(code: string) {
  const messages: Record<string, string> = {
    source_description_only: "ওয়েবসাইটে শুধু বইয়ের পরিচিতি আছে, পড়ার লেখা নেই। অ্যাপ পরে আবার পরীক্ষা করবে।",
    source_layout_unknown: "ওয়েবসাইটের লেখার ধরন শনাক্ত করা যায়নি। ভুল বই প্রকাশ না করে অ্যাপ পরে আবার পরীক্ষা করবে।",
    source_access_unavailable: "ওয়েবসাইট এখন লেখাটি খুলতে দিচ্ছে না। অ্যাপ পরে আবার চেষ্টা করবে।",
    source_missing: "ওয়েবসাইটে বইয়ের পাতাটি এখন পাওয়া যাচ্ছে না। অ্যাপ আগামী দিন আবার পরীক্ষা করবে।",
    source_connection_unavailable: "ওয়েবসাইটের সঙ্গে সংযোগ হয়নি। সংরক্ষিত অগ্রগতি থেকে স্বয়ংক্রিয়ভাবে আবার চেষ্টা হবে।",
    source_circuit_open: "ওয়েবসাইটে বারবার সংযোগ ব্যর্থ হওয়ায় কিছুক্ষণ বিরতি দেওয়া হয়েছে। কাজ নিজে থেকেই আবার চলবে।",
    source_url_not_allowed: "বইয়ের লিংকটি নির্ধারিত ওয়েবসাইটের নয়। লিংক ও ওয়েবসাইটের সেটিংস পরীক্ষা করুন।",
    mail_acceptance_unknown: "ইমেইল সার্ভার বার্তাটি গ্রহণ করেছে কি না নিশ্চিত নয়। আবার পাঠানোর আগে যাচাই করুন।",
    source_duplicate: "একই নামে আরেকটি বই পাওয়া গেছে। বই দুটি মিলিয়ে সিদ্ধান্ত নিন।",
    source_incomplete: "বইয়ের সব লেখা পাওয়া যায়নি। সংগ্রহের ফল পরীক্ষা করুন।",
    source_export_content_mismatch: "তৈরি ফাইলের লেখা ওয়েবসাইটের সংগৃহীত লেখার সঙ্গে মেলেনি। ফাইল আবার তৈরি করতে হবে।",
    source_verification_missing: "স্বয়ংক্রিয় যাচাই সম্পূর্ণ হয়নি। বইটি আবার প্রসেস করুন।",
    source_content_incomplete: "বইয়ের সব লেখা পাওয়া যায়নি। সংগ্রহের ফল পরীক্ষা করুন।",
    source_content_unavailable: "ওয়েবসাইটে অধ্যায়ের লেখা এখন পাওয়া যাচ্ছে না। অ্যাপ আবার স্বয়ংক্রিয়ভাবে পরীক্ষা করবে।",
    source_metadata_incomplete: "বইয়ের নাম বা প্রয়োজনীয় তথ্য পাওয়া যায়নি। তথ্য পরীক্ষা করে আবার সংগ্রহ করুন।",
    source_catalog_layout_unrecognized: "ওয়েবসাইটের পাতায় বইয়ের তালিকা শনাক্ত করা যায়নি। এই পাতার বই সংরক্ষণের আগেই সংগ্রহ থেমেছে।",
    source_catalog_empty: "ওয়েবসাইটের তালিকায় কোনো বই পাওয়া যায়নি। ঠিকানা পরীক্ষা করে আবার সংগ্রহ করুন।",
    source_catalog_scan_limit: "তালিকা সংগ্রহের নিরাপদ সীমা পূর্ণ হয়েছে। সব পাতা সংগ্রহ হয়নি; আগের তথ্য সংরক্ষিত আছে।",
    catalog_processing_already_active: "সব বই তৈরির আরেকটি কাজ চলছে। সেটির অবস্থা দেখুন।",
    source_catalog_pagination_stalled: "ওয়েবসাইট পরের পাতাতেও একই বই ফেরত দিয়েছে। আগের পাতার বইগুলো সংরক্ষিত আছে।",
    source_catalog_pagination_invalid: "ওয়েবসাইটের পরের পাতার ঠিকানা সঠিক নয়। তালিকা সংগ্রহ থেমেছে।",
    source_discovery_metadata_invalid: "তালিকার কোনো বইয়ের নাম বা লিংক সঠিকভাবে পাওয়া যায়নি। সংগ্রহ থেমেছে।",
  };
  return Object.hasOwn(messages, code) ? messages[code] : "কাজটি শেষ করা যায়নি। বিস্তারিত খুলে সমস্যাটি দেখুন।";
}

export function waitDuration(seconds: number) {
  const units = [{ size: 86400, label: "দিন" }, { size: 3600, label: "ঘণ্টা" }, { size: 60, label: "মিনিট" }];
  const unit = units.find((candidate) => seconds >= candidate.size);
  return unit ? { value: Math.floor(seconds / unit.size), label: unit.label } : { value: seconds, label: "সেকেন্ড" };
}

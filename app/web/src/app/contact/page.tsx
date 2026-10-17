import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
export async function generateMetadata() { return localizeMetadata({ title: "যোগাযোগ", alternates: { canonical: "/contact/" },
  description: "বইয়ের তথ্যে ভুল বা অ্যাকাউন্টের সমস্যা সম্পর্কে পাঠাগারের পরিচালকের সঙ্গে যোগাযোগের নির্দেশনা।" }); }

export default function ContactPage() {
  const email = process.env.PUBLIC_CONTACT_EMAIL;
  return <article className="article"><p className="eyebrow"><SiteText>{"আপনার মতামত"}</SiteText></p><h1><SiteText>{"যোগাযোগ"}</SiteText></h1>
    <p><SiteText>{"বইয়ের তথ্যে কোনো ভুল দেখলে বইয়ের নাম, ক্যাটালগ নম্বর এবং সংশোধনের নির্ভরযোগ্য উৎস উল্লেখ করুন। অ্যাকাউন্টের সমস্যা জানাতে কোন পাতায় কী সমস্যা হচ্ছে তা লিখুন।"}</SiteText></p>
    {email ? <p><SiteText>{"পাঠাগারের পরিচালকের ইমেইল: "}</SiteText><a className="text-link" href={`mailto:${email}`}>{email}</a></p>
      : <p><SiteText>{"অ্যাকাউন্টের আমন্ত্রণ যিনি পাঠিয়েছেন, তাঁর সঙ্গে যোগাযোগ করুন।"}</SiteText></p>}
    <p><SiteText>{"যোগাযোগের বার্তায় পাসওয়ার্ড বা দুই ধাপের যাচাইয়ের কোড পাঠাবেন না।"}</SiteText></p>
  </article>;
}

import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
export async function generateMetadata() { return localizeMetadata({ title: "আমাদের সম্পর্কে", alternates: { canonical: "/about/" },
  description: "বিশ্বজুড়ে বাংলা পাঠকের জন্য বাংলা পাঠাগারের উদ্দেশ্য ও বই প্রকাশের নীতি।" }); }

export default function AboutPage() {
  return <article className="article"><p className="eyebrow"><SiteText>{"বাংলা পাঠাগার"}</SiteText></p><h1><SiteText>{"বাংলা বইয়ের সঙ্গে সংযোগ"}</SiteText></h1>
    <p><SiteText>{"বাংলা ভাষার পাঠক ছড়িয়ে আছেন সারা পৃথিবীতে। বাংলা পাঠাগার বইয়ের পরিচিতি, লেখক ও সংস্করণের তথ্য এক জায়গায় এনে সেই পাঠকদের বই খুঁজতে সাহায্য করে।"}</SiteText></p>
    <h2><SiteText>{"বইয়ের পরিচিতি সবার জন্য"}</SiteText></h2><p><SiteText>{"প্রকাশিত বইয়ের নাম, লেখক ও পরিচিতি অ্যাকাউন্ট ছাড়াই দেখা যায়। প্রস্তুতি ও স্বয়ংক্রিয় যাচাই সফল হলে বই প্রকাশিত হয়।"}</SiteText></p>
    <h2><SiteText>{"আপনার নিজের পাঠের জায়গা"}</SiteText></h2><p><SiteText>{"অ্যাকাউন্টে যুক্ত বই, পড়ার অবস্থান ও ব্যক্তিগত নোট আপনার পাঠের অংশ। বই পড়া, ডাউনলোড করা ও কিন্ডলে পাঠানোর সুযোগ বই এবং অ্যাকাউন্টের অনুমতির ওপর নির্ভর করে।"}</SiteText></p>
    <h2><SiteText>{"তথ্যের মান"}</SiteText></h2><p><SiteText>{"একই বইয়ের ভিন্ন সংস্করণ এবং একই নামের লেখক আলাদা হতে পারেন। লেখক, সংস্করণ বা প্রকাশনার তথ্য যাচাই করতে বইয়ের ক্যাটালগ নম্বর ব্যবহার করুন।"}</SiteText></p>
  </article>;
}

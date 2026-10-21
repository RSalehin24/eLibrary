import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import Link from "next/link";

export async function generateMetadata() { return localizeMetadata({ title: "সহায়তা", alternates: { canonical: "/help/" },
  description: "বাংলা বই খোঁজা, অ্যাকাউন্টে প্রবেশ এবং ব্যক্তিগত পাঠাগার ব্যবহারের সহায়তা।" }); }

export default function HelpPage() {
  return <article className="article"><p className="eyebrow"><SiteText>{"পাঠের সহায়তা"}</SiteText></p><h1><SiteText>{"পাঠাগার ব্যবহার করুন"}</SiteText></h1>
    <h2><SiteText>{"কীভাবে বই খুঁজব?"}</SiteText></h2><p><Link className="text-link" href="/catalog/"><SiteText>{"বইয়ের পাঠাগারে"}</SiteText></Link><SiteText>{" বই বা লেখকের বাংলা নাম লিখুন। পুরো নাম না জানলে নামের একটি অংশ দিয়ে খুঁজুন। বইয়ের ক্যাটালগ নম্বর জানা থাকলে সেটিও ব্যবহার করতে পারেন।"}</SiteText></p>
    <h2><SiteText>{"অ্যাকাউন্টে কীভাবে প্রবেশ করব?"}</SiteText></h2><p><Link className="text-link" href="/login/"><SiteText>{"প্রবেশের পাতায়"}</SiteText></Link><SiteText>{" আপনার ইমেইল ও পাসওয়ার্ড লিখুন। দুই ধাপের যাচাই চালু থাকলে আপনার অথেনটিকেটর অ্যাপের বর্তমান কোড দিন।"}</SiteText></p>
    <h2><SiteText>{"আমার বই কোথায়?"}</SiteText></h2><p><SiteText>{"প্রবেশের পরে "}</SiteText><Link className="text-link" href="/my-books/"><SiteText>{"আমার বইয়ে"}</SiteText></Link><SiteText>{" আপনার অ্যাকাউন্টে যুক্ত বই পাওয়া যাবে। পড়ার অবস্থান অন্য পাঠকের সঙ্গে ভাগ করা হয় না।"}</SiteText></p>
    <h2><SiteText>{"পরিচিতি দেখলেই কি পড়তে পারব?"}</SiteText></h2><p><SiteText>{"বইয়ের পরিচিতি সবার জন্য খোলা। পড়া, ডাউনলোড ও কিন্ডলে পাঠানোর জন্য আপনার অ্যাকাউন্টে সংশ্লিষ্ট অনুমতি থাকতে হবে।"}</SiteText></p>
    <h2><SiteText>{"ইন্টারনেট ছাড়া ব্যবহার করা যাবে?"}</SiteText></h2><p><Link className="button button-quiet" href="/local-reader/"><SiteText>নিজের EPUB পড়ুন</SiteText></Link></p><p><SiteText>{"নিজের EPUB পড়ার পাতাটি একবার খুললে ইন্টারনেট ছাড়াও ডিভাইসের ফাইল পড়তে পারবেন। পাঠাগারের সংরক্ষিত বই, নোট ও অ্যাকাউন্টের কাজের জন্য ইন্টারনেট প্রয়োজন।"}</SiteText></p>
    <h2 id="install"><SiteText>{"অ্যাপ কীভাবে ইনস্টল করব?"}</SiteText></h2><p><SiteText>{"সমর্থিত Chrome-এ এই সাইট খুলুন। নিচে ‘অ্যাপ ইনস্টল করুন’ থাকলে সেটি চাপুন। বোতাম না থাকলে Chrome-এর মেনুতে ‘Install app’, ‘Install page as app’ বা ‘Add to Home screen’ দেখুন। ফোন, ট্যাবলেট ও কম্পিউটারভেদে নাম আলাদা হতে পারে।"}</SiteText></p>
    <p><SiteText>{"iPhone-এ Safari দিয়ে এই সাইট খুলুন। Share মেনু থেকে ‘Add to Home Screen’ বেছে নিন। ‘Open as Web App’ দেখা গেলে সেটি চালু রেখে ‘Add’ চাপুন।"}</SiteText></p>
    <p><SiteText>{"ইনস্টল করা অ্যাপ আইকন থেকে আলাদা জানালায় খুলতে পারে। কিছু ডিভাইসে কেবল হোম স্ক্রিনের শর্টকাট পাওয়া যায়। ব্রাউজারেও সব কাজ করতে পারবেন। পাঠাগারের বই পড়তে ইন্টারনেট লাগবে; নিজের EPUB ফাইল অফলাইনেও খুলতে পারবেন।"}</SiteText></p>
  </article>;
}

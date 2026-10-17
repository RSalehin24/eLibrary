import { SiteText } from "@/components/site-language";
import Link from "next/link";

export default function NotFoundPage() {
  return <section className="empty-state"><h1><SiteText>{"পাতাটি পাওয়া যায়নি"}</SiteText></h1><p><SiteText>{"বইটি প্রকাশিত না-ও হতে পারে, অথবা ঠিকানাটি বদলে গেছে।"}</SiteText></p>
    <Link className="button" href="/catalog/"><SiteText>{"পাঠাগারে ফিরে যান"}</SiteText></Link></section>;
}

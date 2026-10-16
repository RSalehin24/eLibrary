import Link from "next/link";
import { siteName } from "@/lib/site";
import { AccountMenu } from "./account-menu";
import { BrandMark } from "./brand-mark";

export function SiteHeader() {
  return <header className="site-header">
    <Link href="/" className="brand" aria-label={siteName}><BrandMark /><span className="brand-copy"><span>{siteName}</span><small>বাংলা বই, আপনার পৃথিবী</small></span></Link>
    <nav aria-label="প্রধান নেভিগেশন">
      <Link href="/catalog/">বই খুঁজুন</Link><Link href="/help/">সহায়তা</Link>
      <Link href="/my-books/">আমার বই</Link>
    </nav>
    <AccountMenu />
  </header>;
}

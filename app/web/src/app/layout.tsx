import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { QueryProvider } from "@/components/query-provider";
import { SiteHeader } from "@/components/site-header";
import { BrandMark } from "@/components/brand-mark";
import { PWAControls } from "@/components/pwa-controls";
import { siteName, siteOrigin } from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin()), title: { default: siteName, template: `%s | ${siteName}` },
  description: "বিশ্বজুড়ে বাংলা পাঠকের জন্য বইয়ের পরিচিতি, লেখক ও ব্যক্তিগত পাঠাগার।",
  icons: { icon: "/icons/book-192-v2.png", apple: "/icons/book-192-v2.png" },
  verification: { google: process.env.GOOGLE_SITE_VERIFICATION, other: process.env.BING_SITE_VERIFICATION ? { "msvalidate.01": process.env.BING_SITE_VERIFICATION } : {} },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#173e35" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="bn" data-scroll-behavior="smooth"><body><QueryProvider>
    <a className="skip-link" href="#main">মূল বিষয়ে যান</a><SiteHeader />
    <main id="main" className="page-container">{children}</main>
    <footer className="site-footer"><div className="footer-brand"><BrandMark size={36} /><span><strong>{siteName}</strong><small>বাংলা বই, সবার কাছে</small></span></div>
      <nav aria-label="অতিরিক্ত তথ্য"><Link href="/about/">আমাদের সম্পর্কে</Link><Link href="/contact/">যোগাযোগ</Link></nav><PWAControls />
    </footer>
  </QueryProvider></body></html>;
}

import { localizeMetadata } from "@/lib/metadata-language";
import type { Viewport } from "next";
import Link from "next/link";
import { QueryProvider } from "@/components/query-provider";
import { SiteHeader } from "@/components/site-header";
import { BrandMark } from "@/components/brand-mark";
import { PWAControls } from "@/components/pwa-controls";
import { siteName, siteOrigin } from "@/lib/site";
import "./globals.css";
import "./product.css";
import { libraryFont } from "@/lib/fonts";
import { SiteLanguageProvider, SiteText, SiteNav } from "@/components/site-language";
import { getAdminLanguage } from "@/lib/admin-language-server";
import { NotificationProvider } from "@/components/notification-provider";

export async function generateMetadata() { return localizeMetadata({
  metadataBase: new URL(siteOrigin()), title: { default: siteName, template: `%s | ${siteName}` },
  description: "বিশ্বজুড়ে বাংলা পাঠকের জন্য বইয়ের পরিচিতি, লেখক ও ব্যক্তিগত পাঠাগার।",
  icons: { icon: "/icons/book-192-v2.png", apple: "/icons/book-192-v2.png" },
  verification: { google: process.env.GOOGLE_SITE_VERIFICATION, other: process.env.BING_SITE_VERIFICATION ? { "msvalidate.01": process.env.BING_SITE_VERIFICATION } : {} },
}); }
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#173e35" };

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const language = await getAdminLanguage();
  return <html lang={language}><body className={libraryFont.variable}><QueryProvider><SiteLanguageProvider initial={language}><NotificationProvider>
    <a className="skip-link" href="#main"><SiteText>{"মূল বিষয়ে যান"}</SiteText></a><SiteHeader />
    <main id="main" className="page-container">{children}</main>
    <footer className="site-footer"><div className="footer-brand"><BrandMark size={36} /><span><strong><SiteText>{siteName}</SiteText></strong><small><SiteText>{"বাংলা বই, সবার কাছে"}</SiteText></small></span></div>
      <SiteNav aria-label="অতিরিক্ত তথ্য"><Link href="/about/"><SiteText>{"আমাদের সম্পর্কে"}</SiteText></Link><Link href="/contact/"><SiteText>{"যোগাযোগ"}</SiteText></Link></SiteNav><PWAControls />
    </footer>
  </NotificationProvider></SiteLanguageProvider></QueryProvider></body></html>;
}

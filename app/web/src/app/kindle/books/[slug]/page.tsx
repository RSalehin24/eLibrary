import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { KindleOptions } from "@/api/types";
import { KindleComposer } from "@/components/kindle-composer";
import { routeSlug } from "@/lib/route-slug";
import { requireReader } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "কিন্ডলে বই পাঠান" }); }

export default async function KindleBookPage({ params }: { params: Promise<{ slug: string }> }) {
  const slug = routeSlug((await params).slug);
  await requireReader(`/kindle/books/${encodeURIComponent(slug)}/`);
  let options: KindleOptions;
  try { options = await sessionRequest<KindleOptions>(`delivery/books/${encodeURIComponent(slug)}/kindle/`); }
  catch (error) {
    if (error instanceof APIError && error.status === 404) notFound();
    if (error instanceof APIError && [403, 409].includes(error.status)) return <><h1><SiteText>{"কিন্ডলে বই পাঠান"}</SiteText></h1><p className="notice"><SiteText>{"এই বই পাঠানোর অনুমতি বা প্রস্তুত EPUB এখন পাওয়া যাচ্ছে না।"}</SiteText></p><Link className="text-link" href="/my-books/"><SiteText>{"নিজের বইয়ে ফিরুন"}</SiteText></Link></>;
    throw error;
  }
  return <><Link className="text-link" href="/kindle/"><SiteText>{"← অনুরোধের তালিকা"}</SiteText></Link><h1>{options.book.title}</h1><KindleComposer initial={options} /></>;
}

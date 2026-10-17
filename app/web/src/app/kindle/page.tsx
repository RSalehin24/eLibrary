import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import { sessionRequest } from "@/api/server";
import type { KindleCollection } from "@/api/types";
import { KindleHistory } from "@/components/kindle-history";
import { requireReader } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "কিন্ডলে পাঠানোর অনুরোধ" }); }

export default async function KindlePage() {
  await requireReader("/kindle/");
  const initial = await sessionRequest<KindleCollection>("me/kindle/");
  return <><p className="eyebrow"><SiteText>{"আপনার ব্যক্তিগত পাঠাগার"}</SiteText></p><h1><SiteText>{"কিন্ডলে পাঠানোর অনুরোধ"}</SiteText></h1><KindleHistory initial={initial} /></>;
}

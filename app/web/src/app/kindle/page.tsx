import { sessionRequest } from "@/api/server";
import type { KindleCollection } from "@/api/types";
import { KindleHistory } from "@/components/kindle-history";
import { requireReader } from "@/lib/workspace-session";

export const metadata = { title: "কিন্ডলে পাঠানোর অনুরোধ" };

export default async function KindlePage() {
  await requireReader("/kindle/");
  const initial = await sessionRequest<KindleCollection>("me/kindle/");
  return <><p className="eyebrow">আপনার ব্যক্তিগত পাঠাগার</p><h1>কিন্ডলে পাঠানোর অনুরোধ</h1><KindleHistory initial={initial} /></>;
}

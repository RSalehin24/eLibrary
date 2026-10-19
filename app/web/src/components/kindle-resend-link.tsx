import Link from "next/link";
import type { KindleOperation } from "@/api/types";
import { kindleCanResend, kindleResendHref } from "@/lib/kindle-history";
import { SiteText } from "./site-language";
import { Icon } from "./icon";

export function KindleResendLink({ operation }: { operation: KindleOperation }) {
  return kindleCanResend(operation.state) ? <Link className="button button-quiet" href={kindleResendHref(operation)}><Icon name="send" /><SiteText>পুনরায় পাঠান</SiteText></Link> : null;
}

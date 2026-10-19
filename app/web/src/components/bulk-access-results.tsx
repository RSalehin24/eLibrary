"use client";

import type { ManagedGrantBulkResult, ManagedGrantCreate } from "@/api/types";
import type { BulkAccessTarget } from "@/lib/bulk-access";
import { accessScopes } from "@/lib/access-status";
import { AdminNumber, AdminText, useAdminLanguage } from "./admin-language";
import { SiteFieldErrors } from "./site-field-errors";

export function BulkAccessResults({ result, requests, targets }: { result: ManagedGrantBulkResult; requests: ManagedGrantCreate[]; targets: BulkAccessTarget[] }) {
  const { t } = useAdminLanguage();
  return <section className="bulk-access-results" aria-label={t("অনুমতির ফলাফল")}><h3><AdminText>{"অনুমতির ফলাফল"}</AdminText></h3>
    <p role="status"><AdminText>{"যোগ হয়েছে: "}</AdminText><AdminNumber value={result.created_count} /><AdminText>{" · আগে সংরক্ষিত: "}</AdminText><AdminNumber value={result.existing_count} /><AdminText>{" · যোগ হয়নি: "}</AdminText><AdminNumber value={result.rejected_count} /></p>
    {!!result.rejected_count && <p className="notice"><AdminText>{"যে অনুমতিগুলো যোগ হয়েছে, সেগুলো কার্যকর আছে। যোগ না হওয়া অনুমতির কারণ দেখে নির্বাচন ঠিক করুন।"}</AdminText></p>}
    <ul className="bulk-access-outcomes">{result.entries.map((entry) => {
      const request = requests[entry.index], targetId = request?.book ?? request?.category ?? request?.contributor;
      const label = targets.find((target) => target.id === targetId)?.name;
      return <li key={entry.index}><strong>{label ?? <AdminText>{"সব বই"}</AdminText>}</strong><span><AdminText>{request ? accessScopes[request.scope] : "অনুমতি"}</AdminText></span>
        <span className="status-label"><AdminText>{entry.status === "created" ? "যোগ হয়েছে" : entry.status === "existing" ? "আগেই সংরক্ষিত" : entry.status === "conflict" ? "অনুমতি আগে থেকেই আছে বা বদলেছে" : entry.status === "forbidden" ? "এই অনুমতি যোগ করার অধিকার নেই" : "যোগ করা যায়নি"}</AdminText></span>
        {Object.values(entry.field_errors).flat().length > 0 && <p className="field-error"><SiteFieldErrors errors={Object.values(entry.field_errors).flat()} /></p>}
      </li>;
    })}</ul>
  </section>;
}

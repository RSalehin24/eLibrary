"use client";

import Link from "next/link";
import type { SourceAutomation } from "@/api/types";
import { automationFrequencies } from "@/lib/automation-status";
import { AdminDate, useAdminLanguage } from "./admin-language";
import { AutomationRunAction } from "./automation-run-now";
import { Icon } from "./icon";

export function AutomationListRow({ schedule }: { schedule: SourceAutomation }) {
  const { t, number } = useAdminLanguage();
  return <tr><th scope="row"><div className="admin-record-identity"><span className="admin-record-icon"><Icon name="schedule" size={22} /></span><div className="admin-record-copy">
    <Link href={`/manage/automations/${schedule.id}/`}>{schedule.name}</Link><span className="automation-row-status"><span className="admin-status" data-status={schedule.enabled ? "active" : "paused"}><span aria-hidden="true" />{t(schedule.enabled ? "সক্রিয়" : "বন্ধ")}</span><span>{t(automationFrequencies[schedule.frequency])}</span></span>
  </div></div></th>
    <td data-label={t("কী কাজ চলবে")}><span>{t(schedule.process_all ? "সব যোগ্য বই তৈরি" : schedule.processing_limit ? "নির্দিষ্ট সংখ্যক বই তৈরি" : "শুধু তালিকা সংগ্রহ")}</span>
      <small>{t(schedule.catalog_scope === "unfinished" ? "অসম্পূর্ণ বই" : "সব বই")}{!schedule.process_all && schedule.processing_limit > 0 && <> · {t("সর্বোচ্চ")} {number(schedule.processing_limit)}</>}</small></td>
    <td data-label={t("পরের নির্ধারিত সময়")}>
      {schedule.enabled ? <><AdminDate value={schedule.next_run_at} /><small>{t("ঢাকার সময়")}</small></> : <span className="muted">{t("সময়সূচি বন্ধ আছে")}</span>}
      <small>{t("যাঁর অনুমতিতে চলবে:")} {schedule.run_as_name}</small>
    </td>
    <td className="admin-record-actions"><div className="automation-row-actions"><AutomationRunAction automation={schedule} /><Link className="button button-quiet" href={`/manage/automations/${schedule.id}/`}><Icon name="settings" />{t("সেটিংস ও ইতিহাস")}</Link></div></td>
  </tr>;
}

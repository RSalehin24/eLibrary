"use client";

import { useId, useState } from "react";
import { readJSON } from "@/api/http";
import { catalogFilterKeys } from "@/lib/catalog-filters";
import { Icon } from "./icon";
import { useSiteLanguage } from "./site-language";

type ExportScope = "catalog" | "library" | "managed" | "physical";
const endpoints: Record<ExportScope, string> = {
  catalog: "catalog/exports/", library: "me/books/export/",
  managed: "manage/book-exports/", physical: "catalog/physical-books/export/",
};
const groupLabels = { "": ["একসঙ্গে", "No grouping"], category: ["বিভাগ অনুযায়ী", "By category"], publisher: ["প্রকাশক অনুযায়ী", "By publisher"], binding: ["বাঁধাই অনুযায়ী", "By binding"], language: ["ভাষা অনুযায়ী", "By language"], contributor: ["লেখক ও সহযোগী অনুযায়ী", "By contributor"] };

export function CatalogExportControls({ filters, scope = "catalog" }: { filters: Readonly<Record<string, string>>; scope?: ExportScope }) {
  const { language } = useSiteLanguage();
  const groupingId = useId();
  const text = (bn: string, en: string) => language === "bn" ? bn : en;
  const [grouping, setGrouping] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  function exportURL(format: string) {
    const allowed = [...catalogFilterKeys, "q", "view", "writer", "translator", "editor", "publisher", "binding", "language", "state", "quality"];
    const parameters = new URLSearchParams(Object.entries(filters).filter(([key, value]) => allowed.includes(key) && value));
    parameters.set("export_format", format);
    if (scope === "physical") parameters.set("group_by", grouping);
    return `/api/v1/${endpoints[scope]}?${parameters}`;
  }
  async function download(format: string) {
    setBusy(format); setMessage(""); setFailed(false);
    try {
      const response = await fetch(exportURL(format), { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) await readJSON(response);
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `${scope === "physical" ? "physical-books" : "books"}.${format}`;
      document.body.append(anchor); anchor.click(); anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage(text("ফাইল ডাউনলোড হয়েছে।", "File downloaded."));
    } catch {
      setFailed(true); setMessage(text("ফাইল তৈরি করা যায়নি। আবার চেষ্টা করুন। বাংলা PDF-এর জন্য সার্ভারে বাংলা ফন্ট ও টেক্সট শেপিং চালু থাকতে হবে।", "Could not create the file. Try again. Bengali PDF requires the server’s Bengali font and text shaping support."));
    } finally { setBusy(""); }
  }
  return <section className="catalog-export-controls" aria-label={text("বইয়ের তালিকা ডাউনলোড", "Download book list")}>
    <div className="editorial-actions"><strong>{text("তালিকা ডাউনলোড", "Download list")}</strong>
      {scope === "physical" && <div className="catalog-filter-field"><label htmlFor={groupingId}>{text("ভাগ করুন", "Group by")}</label><select id={groupingId} value={grouping} onChange={(event) => setGrouping(event.target.value)} disabled={!!busy}>
        {Object.entries(groupLabels).map(([value, labels]) => <option key={value} value={value}>{labels[language === "bn" ? 0 : 1]}</option>)}
      </select></div>}
      {(scope === "physical" ? ["csv", "pdf", "xlsx"] : ["csv", "pdf"]).map(format => <button className="button button-quiet" type="button" key={format} onClick={() => void download(format)} disabled={!!busy} aria-busy={busy === format}>
        <Icon name="download" />{format.toUpperCase()}{busy === format ? text(" তৈরি হচ্ছে…", " generating…") : ""}
      </button>)}
      <a className="button button-quiet" href={exportURL("print")} target="_blank" rel="noopener"><Icon name="external" />{text("প্রিন্ট / PDF হিসেবে সংরক্ষণ", "Print / Save as PDF")}</a>
    </div><p className="muted">{text("বর্তমান ফিল্টারের সব বই থাকবে। শুধু এই পাতার বই নয়।", "Includes every book matching these filters, across all pages.")}</p>
    {message && <p role={failed ? "alert" : "status"} className={failed ? "field-error" : "success-message"}>{message}</p>}
  </section>;
}

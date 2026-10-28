"use client";

import { useState } from "react";
import { readJSON } from "@/api/http";
import { catalogFilterKeys } from "@/lib/catalog-filters";
import { Icon } from "./icon";
import { useSiteLanguage } from "./site-language";

type ExportScope = "catalog" | "library" | "managed";
const endpoints: Record<ExportScope, string> = {
  catalog: "catalog/exports/", library: "me/books/export/",
  managed: "manage/book-exports/",
};

export function CatalogExportControls({ filters, scope = "catalog" }: { filters: Readonly<Record<string, string>>; scope?: ExportScope }) {
  const { language } = useSiteLanguage();
  const text = (bn: string, en: string) => language === "bn" ? bn : en;
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  function exportURL(format: string) {
    const allowed = [...catalogFilterKeys, "q", "view"];
    const parameters = new URLSearchParams(Object.entries(filters).filter(([key, value]) => allowed.includes(key) && value));
    parameters.set("export_format", format);
    return `/api/v1/${endpoints[scope]}?${parameters}`;
  }
  async function download(format: string) {
    setBusy(format); setMessage(""); setFailed(false);
    try {
      const response = await fetch(exportURL(format), { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) await readJSON(response);
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `books.${format}`;
      document.body.append(anchor); anchor.click(); anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage(text("ফাইল ডাউনলোড হয়েছে।", "File downloaded."));
    } catch {
      setFailed(true); setMessage(text("ফাইল তৈরি করা যায়নি। আবার চেষ্টা করুন। বাংলা PDF-এর জন্য সার্ভারে বাংলা ফন্ট ও টেক্সট শেপিং চালু থাকতে হবে।", "Could not create the file. Try again. Bengali PDF requires the server’s Bengali font and text shaping support."));
    } finally { setBusy(""); }
  }
  return <section className="catalog-export-controls" aria-label={text("বইয়ের তালিকা ডাউনলোড", "Download book list")}>
    <details className="catalog-export-menu" onKeyDown={event => { if (event.key === "Escape") { event.currentTarget.open = false; event.currentTarget.querySelector("summary")?.focus(); } }}>
      <summary className="button button-quiet"><Icon name="download" />{text("তালিকা ডাউনলোড", "Download list")}<Icon name="chevron" /></summary>
      <div className="catalog-export-panel"><p className="muted">{text("বর্তমান ফিল্টারের সব বই থাকবে। শুধু এই পাতার বই নয়।", "Includes every book matching these filters, across all pages.")}</p>
      <div className="catalog-export-options">{["csv", "pdf"].map(format => <button className="button button-quiet" type="button" key={format} onClick={() => void download(format)} disabled={!!busy} aria-busy={busy === format}>
        <Icon name="download" />{format.toUpperCase()}{busy === format ? text(" তৈরি হচ্ছে…", " generating…") : ""}
      </button>)}
      <a className="button button-quiet" href={exportURL("print")} target="_blank" rel="noopener" aria-label={text("প্রিন্ট / PDF হিসেবে সংরক্ষণ", "Print / Save as PDF")}><Icon name="external" />{text("প্রিন্ট", "Print")}</a></div>
    </div></details>
    {message && <p role={failed ? "alert" : "status"} className={failed ? "field-error" : "success-message"}>{message}</p>}
  </section>;
}

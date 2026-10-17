"use client";

import { SiteText } from "@/components/site-language";

import Link from "next/link";
import { useState } from "react";
import { createPortal } from "react-dom";
import { useInstallPrompt } from "@/lib/pwa-install";
import { useServiceWorker } from "@/lib/pwa-registration";
import { useUpdateSafety } from "@/lib/update-safety";

export function PWAControls() {
  const installation = useInstallPrompt();
  const worker = useServiceWorker();
  const safety = useUpdateSafety();
  const [blocked, setBlocked] = useState(false);
  const [preparing, setPreparing] = useState(false);
  async function acceptUpdate() { setPreparing(true); const ready = await safety.prepare(); setPreparing(false); setBlocked(!ready); if (ready) worker.activate(); }
  return <div className="pwa-controls">{installation.available && <button className="button button-quiet" onClick={() => void installation.install()}><SiteText>{"অ্যাপ ইনস্টল করুন"}</SiteText></button>}
    {!installation.installed && <Link className="text-link" href="/help/#install"><SiteText>{"ইনস্টলের সহায়তা"}</SiteText></Link>}
    {(installation.failed || worker.failed) && <p className="muted" role="status"><SiteText>{"অ্যাপের সুবিধা প্রস্তুত হয়নি। এই পাতায় অনলাইনে কাজ চালিয়ে যেতে পারবেন।"}</SiteText></p>}
    {worker.waiting && createPortal(<div className="pwa-controls pwa-update notice" role="status"><p><SiteText>{"নতুন সংস্করণ প্রস্তুত। আপনার কাজ শেষ হলে হালনাগাদ করুন।"}</SiteText></p><button className="button button-quiet" disabled={preparing} onClick={() => void acceptUpdate()}><SiteText>{"হালনাগাদ করে আবার খুলুন"}</SiteText></button>
      {blocked && <p role="alert"><SiteText>{"অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন। পড়ার অবস্থান সংরক্ষণে সমস্যা হলে আবার চেষ্টা করুন।"}</SiteText></p>}</div>, document.body)}
  </div>;
}

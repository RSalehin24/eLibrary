"use client";

import Link from "next/link";
import { useState } from "react";
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
  return <div className="pwa-controls">{installation.available && <button className="button button-quiet" onClick={() => void installation.install()}>অ্যাপ ইনস্টল করুন</button>}
    {!installation.installed && <Link className="text-link" href="/help/#install">ইনস্টলের সহায়তা</Link>}
    {(installation.failed || worker.failed) && <p className="muted" role="status">অ্যাপের সুবিধা প্রস্তুত হয়নি। এই পাতায় অনলাইনে কাজ চালিয়ে যেতে পারবেন।</p>}
    {worker.waiting && <div className="notice" role="status"><p>নতুন সংস্করণ প্রস্তুত। আপনার কাজ শেষ হলে হালনাগাদ করুন।</p><button className="button button-quiet" disabled={preparing} onClick={() => void acceptUpdate()}>হালনাগাদ করে আবার খুলুন</button>
      {blocked && <p role="alert">অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন। পড়ার অবস্থান সংরক্ষণে সমস্যা হলে আবার চেষ্টা করুন।</p>}</div>}
  </div>;
}

"use client";

import { useState } from "react";
import { useSiteLanguage } from "./site-language";

export function AuthenticatorSetupLink({ uri }: { uri: string }) {
  const { t } = useSiteLanguage();
  const [message, setMessage] = useState(""), [failed, setFailed] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(uri); setFailed(false); setMessage("সেটআপের লিংক কপি হয়েছে।"); }
    catch { setFailed(true); setMessage("লিংক কপি করা যায়নি। নিচের লিংক নির্বাচন করে কপি করুন।"); }
  }
  return <div><button className="button button-quiet" type="button" onClick={() => void copy()}>{t("সেটআপের লিংক কপি করুন")}</button>
    {message && <p role="status">{t(message)}</p>}
    <details open={failed || undefined}><summary>{t("সেটআপের লিংক দেখুন")}</summary><code className="authenticator-secret">{uri}</code></details>
  </div>;
}

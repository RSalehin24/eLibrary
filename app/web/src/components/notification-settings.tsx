"use client";

import { useNotifications } from "./notification-provider";
import { useSiteLanguage } from "./site-language";

export function NotificationSettings() {
  const { enabled, persistent, setEnabled } = useNotifications();
  const { language } = useSiteLanguage();
  return <section className="account-section" id="profile-notifications">
    <h2>{language === "bn" ? "নোটিফিকেশনের শব্দ" : "Notification sounds"}</h2>
    <p className="muted">{language === "bn" ? "অনুরোধ সফল হলে বা কোনো সমস্যা হলে ছোট একটি শব্দ শুনতে পারেন। প্রথমে শব্দ বন্ধ থাকে। এই ব্রাউজারে আপনার পছন্দ রাখা হবে।" : "Play a short sound when a request succeeds or encounters a problem. Sound is off by default. This preference is saved in this browser."}</p>
    <label className="notification-sound-toggle"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />{language === "bn" ? "নোটিফিকেশনের শব্দ চালু রাখুন" : "Enable notification sounds"}</label>
    {!persistent && <p className="notice">{language === "bn" ? "ব্রাউজারে পছন্দটি সংরক্ষণ করা যায়নি। এই পাতা খোলা থাকা পর্যন্ত এটি কার্যকর থাকবে।" : "This browser could not save your preference. It will apply while this page stays open."}</p>}
  </section>;
}

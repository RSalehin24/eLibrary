import { SiteText, SiteNumber } from "@/components/site-language";
import type { ReaderAppearance } from "@/lib/reader-document";
type SettingsProps = { appearance: ReaderAppearance; onChange: (appearance: ReaderAppearance) => void };
export function ReaderSettings({ appearance, onChange }: SettingsProps) {
  return <div className="reader-settings"><label htmlFor="reader-font-size"><SiteText>অক্ষরের আকার: </SiteText><SiteNumber value={appearance.fontSize} /></label>
    <input id="reader-font-size" type="range" min={16} max={40} step={2} value={appearance.fontSize} onChange={(event) => onChange({ ...appearance, fontSize: Number(event.target.value) })} />
    <label htmlFor="reader-theme"><SiteText>পাতার রং</SiteText></label><select id="reader-theme" value={appearance.theme} onChange={(event) => onChange({ ...appearance, theme: event.target.value as ReaderAppearance["theme"] })}><option value="paper"><SiteText>সাদা</SiteText></option><option value="sepia"><SiteText>হালকা বাদামি</SiteText></option><option value="dark"><SiteText>গাঢ়</SiteText></option></select>
    <label htmlFor="reader-font"><SiteText>অক্ষরের ধরন</SiteText></label><select id="reader-font" value={appearance.font} onChange={event => onChange({ ...appearance, font: event.target.value as ReaderAppearance["font"] })}><option value="serif"><SiteText>সেরিফ</SiteText></option><option value="sans"><SiteText>স্যান্স সেরিফ</SiteText></option><option value="publisher"><SiteText>বইয়ের নিজস্ব অক্ষর</SiteText></option></select>
    <label htmlFor="reader-line-height"><SiteText>লাইনের ফাঁক</SiteText></label><input id="reader-line-height" type="range" min={1.4} max={2.4} step={0.1} value={appearance.lineHeight} onChange={event => onChange({ ...appearance, lineHeight: Number(event.target.value) })} />
    <label htmlFor="reader-width"><SiteText>পাঠের প্রস্থ</SiteText></label><select id="reader-width" value={appearance.width} onChange={event => onChange({ ...appearance, width: Number(event.target.value) })}><option value={640}><SiteText>সরু</SiteText></option><option value={800}><SiteText>মাঝারি</SiteText></option><option value={1040}><SiteText>চওড়া</SiteText></option></select>
    <p className="muted"><SiteText>কিবোর্ড: ← → দিয়ে পাতা, F দিয়ে পূর্ণ পর্দা, Esc দিয়ে ফিরুন।</SiteText> <SiteText>Ctrl/⌘ +/− দিয়ে অক্ষরের আকার, Ctrl/⌘ 1/2/3 দিয়ে পাতার রং বদলান।</SiteText></p>
    <p className="muted"><SiteText>দুইবার ট্যাপ করে পূর্ণ পর্দা খুলুন। দুই আঙুল কাছে বা দূরে সরিয়ে লেখা ছোট-বড় করুন; দুই আঙুল দিয়ে একবার ট্যাপ করে পাতার রং বদলান।</SiteText></p>
  </div>;
}

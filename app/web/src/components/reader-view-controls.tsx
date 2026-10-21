import { SiteText } from "./site-language";
import type { ReaderAppearance } from "@/lib/reader-document";
export function ReaderViewControls({ appearance, onChange }: { appearance: ReaderAppearance; onChange: (value: ReaderAppearance) => void }) {
  return <>
    <div className="reader-view-choice"><label htmlFor="reader-view"><SiteText>পড়ার ধরন</SiteText></label><select id="reader-view" value={appearance.view} aria-describedby={appearance.view === "spread" ? "reader-spread-note" : undefined} onChange={event => onChange({ ...appearance, view: event.target.value as ReaderAppearance["view"] })}><option value="scroll"><SiteText>স্ক্রল করে পড়ুন</SiteText></option><option value="single"><SiteText>এক পৃষ্ঠা</SiteText></option><option value="spread"><SiteText>পাশাপাশি দুই পৃষ্ঠা</SiteText></option></select>{appearance.view === "spread" && <small className="reader-spread-note" id="reader-spread-note"><SiteText>ছোট পর্দায় এক পৃষ্ঠা দেখা যাবে।</SiteText></small>}</div></>;
}

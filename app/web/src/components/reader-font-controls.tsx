import { SiteButton, SiteNumber } from "./site-language";
import type { ReaderAppearance } from "@/lib/reader-preferences";

export function ReaderFontControls({ appearance, onChange }: { appearance: ReaderAppearance; onChange: (value: ReaderAppearance) => void }) {
  return <div className="reader-font-controls">
    <SiteButton className="button button-quiet" aria-label="অক্ষর ছোট করুন" title="অক্ষর ছোট করুন" aria-keyshortcuts="Control+- Meta+-" disabled={appearance.fontSize <= 14} onClick={() => onChange({ ...appearance, fontSize: appearance.fontSize - 2 })}>A−</SiteButton>
    <span><SiteNumber value={appearance.fontSize} /> px</span>
    <SiteButton className="button button-quiet" aria-label="অক্ষর বড় করুন" title="অক্ষর বড় করুন" aria-keyshortcuts="Control+= Meta+=" disabled={appearance.fontSize >= 40} onClick={() => onChange({ ...appearance, fontSize: appearance.fontSize + 2 })}>A+</SiteButton>
  </div>;
}

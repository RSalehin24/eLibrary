import type { ReaderAppearance } from "@/lib/reader-document";

type SettingsProps = { appearance: ReaderAppearance; onChange: (appearance: ReaderAppearance) => void };

export function ReaderSettings({ appearance, onChange }: SettingsProps) {
  return <div className="reader-settings"><label htmlFor="reader-font-size">অক্ষরের আকার: {appearance.fontSize}</label>
    <input id="reader-font-size" type="range" min={16} max={40} step={2} value={appearance.fontSize} onChange={(event) => onChange({ ...appearance, fontSize: Number(event.target.value) })} />
    <label htmlFor="reader-theme">পাতার রং</label><select id="reader-theme" value={appearance.theme} onChange={(event) => {
      const theme = event.target.value;
      if (theme === "paper" || theme === "sepia" || theme === "dark") onChange({ ...appearance, theme });
    }}><option value="paper">সাদা</option><option value="sepia">হালকা বাদামি</option><option value="dark">গাঢ়</option></select></div>;
}

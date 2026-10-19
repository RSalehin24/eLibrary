"use client";

import { useState } from "react";
import { useAdminLanguage } from "./admin-language";

export function TimeInput({ name, initial = "02:00", disabled = false, invalid = false }: { name: string; initial?: string; disabled?: boolean; invalid?: boolean }) {
  const { t, number, language } = useAdminLanguage();
  const [value, setValue] = useState(initial);
  const [hours, minutes] = value.split(":").map(Number);
  const update = (hour: number, minute: number, period: string) => setValue(`${String(hour % 12 + (period === "PM" ? 12 : 0)).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
  const minuteFormat = new Intl.NumberFormat(language, { minimumIntegerDigits: 2, useGrouping: false });
  const hour = hours % 12 || 12, period = hours >= 12 ? "PM" : "AM";
  return <div className="time-input" role="group" aria-label={t("সময়")}>
    <input type="hidden" name={name} value={value} />
    <select id={name} aria-label={t("ঘণ্টা")} value={hour} disabled={disabled} aria-invalid={invalid} onChange={(event) => update(Number(event.target.value), minutes, period)}>{Array.from({ length: 12 }, (_, index) => index + 1).map((item) => <option key={item} value={item}>{number(item)}</option>)}</select>
    <span aria-hidden="true">:</span>
    <select aria-label={t("মিনিট")} value={minutes} disabled={disabled} aria-invalid={invalid} onChange={(event) => update(hour, Number(event.target.value), period)}>{Array.from({ length: 60 }, (_, index) => <option key={index} value={index}>{minuteFormat.format(index)}</option>)}</select>
    <select aria-label={t("দিনের সময়")} value={period} disabled={disabled} onChange={(event) => update(hour, minutes, event.target.value)}><option value="AM">{language === "bn" ? "পূর্বাহ্ণ" : "AM"}</option><option value="PM">{language === "bn" ? "অপরাহ্ণ" : "PM"}</option></select>
  </div>;
}

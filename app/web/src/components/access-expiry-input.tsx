"use client";

import { dhakaDateTimeParts } from "@/lib/bulk-access";
import { AdminText } from "./admin-language";
import { TimeInput } from "./time-input";

export function AccessExpiryInput({ name, initial = null, disabled = false }: { name: string; initial?: string | null; disabled?: boolean }) {
  const value = dhakaDateTimeParts(initial);
  return <fieldset className="access-expiry"><legend><AdminText>{"মেয়াদ শেষ (ঢাকার সময়, ঐচ্ছিক)"}</AdminText></legend>
    <label htmlFor={`${name}-date`}><AdminText>{"তারিখ"}</AdminText></label>
    <input id={`${name}-date`} name={`${name}-date`} type="date" max="9999-12-31" defaultValue={value.date} disabled={disabled} />
    <TimeInput name={`${name}-time`} initial={value.time} disabled={disabled} />
    <p className="muted"><AdminText>{"তারিখ খালি রাখলে মেয়াদ নির্দিষ্ট হবে না। সময় ঢাকার হিসাবে দিন।"}</AdminText></p>
  </fieldset>;
}

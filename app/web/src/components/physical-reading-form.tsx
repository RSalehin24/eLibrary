"use client";

import { useState } from "react";
import type { PhysicalReadingLog, PhysicalReadingLogUpdate } from "@/api/types";
import { updatePhysicalLog } from "@/api/library";
import { useManagedForm, reloadManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";

export function PhysicalReadingForm({ slug, initialLog }: { slug: string; initialLog: PhysicalReadingLog }) {
  const [log, setLog] = useState(initialLog);
  const form = useManagedForm((fields: PhysicalReadingLogUpdate) => updatePhysicalLog(slug, fields), async (updated) => { setLog(updated); });
  return <section className="editorial-workspace"><h2>কাগজের বই পড়ার হিসাব</h2>
    <p className="muted">আপনার পৃষ্ঠা, মূল্যায়ন ও নোট শুধু আপনার অ্যাকাউন্টে থাকবে।</p>
    {form.saving.isSuccess && !form.dirty && <p role="status">পড়ার হিসাব সংরক্ষিত হয়েছে।</p>}
    <form key={log.updated_at ?? "new"} className="editorial-form" onChange={form.markDirty} onSubmit={(event) => {
      event.preventDefault(); if (form.blocked) return; const fields = new FormData(event.currentTarget);
      form.saving.mutate({ expected_updated_at: log.updated_at, status: String(fields.get("status")) as PhysicalReadingLogUpdate["status"], current_page: Number(fields.get("current_page")), total_pages: String(fields.get("total_pages")) ? Number(fields.get("total_pages")) : null, rating: Number(fields.get("rating")), started_on: String(fields.get("started_on")) || null, finished_on: String(fields.get("finished_on")) || null, notes: String(fields.get("notes")) });
    }}><fieldset disabled={form.blocked}><legend>ব্যক্তিগত পাঠের তথ্য</legend>
      <div className="form-field"><label htmlFor="physical-status">পড়ার অবস্থা</label><select id="physical-status" name="status" defaultValue={log.status}><option value="unread">এখনো পড়িনি</option><option value="reading">পড়ছি</option><option value="finished">পড়া শেষ</option></select></div>
      {[{ name: "current_page", label: "বর্তমান পৃষ্ঠা", value: log.current_page, min: 0 }, { name: "total_pages", label: "মোট পৃষ্ঠা (ঐচ্ছিক)", value: log.total_pages ?? "", min: 1 }].map((field) => <div className="form-field" key={field.name}><label htmlFor={field.name}>{field.label}</label><input id={field.name} name={field.name} type="number" min={field.min} max={1000000} step={1} defaultValue={field.value} aria-invalid={!!form.errors[field.name]} />{form.errors[field.name] && <p className="field-error">{form.errors[field.name].join(" ")}</p>}</div>)}
      <div className="form-field"><label htmlFor="physical-rating">আপনার মূল্যায়ন</label><select id="physical-rating" name="rating" defaultValue={log.rating}>{[0, 1, 2, 3, 4, 5].map((value) => <option value={value} key={value}>{value ? `${value} / 5` : "এখনো দিইনি"}</option>)}</select></div>
      {[{ name: "started_on", label: "পড়া শুরুর তারিখ", value: log.started_on }, { name: "finished_on", label: "পড়া শেষের তারিখ", value: log.finished_on }].map((field) => <div className="form-field" key={field.name}><label htmlFor={field.name}>{field.label}</label><input id={field.name} name={field.name} type="date" defaultValue={field.value ?? ""} aria-invalid={!!form.errors[field.name]} />{form.errors[field.name] && <p className="field-error">{form.errors[field.name].join(" ")}</p>}</div>)}
      <div className="form-field"><label htmlFor="physical-notes">পড়ার ব্যক্তিগত নোট</label><textarea id="physical-notes" name="notes" maxLength={20000} rows={6} defaultValue={log.notes} /></div>
    </fieldset><AccountFeedback error={form.saving.error} />
      {form.saving.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm}>বর্তমান হিসাব খুলুন</button>}
      <button className="button" disabled={form.blocked || !form.dirty}>পড়ার হিসাব সংরক্ষণ করুন</button>
    </form></section>;
}

"use client";

import { AdminText } from "@/components/admin-language";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { readAccessReferences } from "@/api/managed-access";
import type { AccessReferenceKind } from "@/api/types";
import { useDebouncedQuery } from "@/lib/debounced-query";

export function AccessTargetSelector({ kind, disabled, errors }: { kind: AccessReferenceKind; disabled: boolean; errors?: string[] }) {
  const [search, setSearch] = useState("");
  const query = useDebouncedQuery(search);
  const references = useQuery({ queryKey: ["private", "access", "references", kind, query], queryFn: ({ signal }) => readAccessReferences(kind, query, signal), refetchOnWindowFocus: false });
  return <fieldset className="access-target"><legend><AdminText>{"অনুমতির লক্ষ্য"}</AdminText></legend>
    <div className="form-field"><label htmlFor="target-search"><AdminText>{"বই, বিভাগ বা লেখকের নাম খুঁজুন"}</AdminText></label><input id="target-search" value={search} maxLength={200} disabled={disabled} onChange={(event) => setSearch(event.target.value)} /></div>
    {references.isFetching && <p role="status"><AdminText>{"খোঁজা হচ্ছে…"}</AdminText></p>}{references.isError && <p role="alert" className="field-error"><AdminText>{"তালিকা পাওয়া যায়নি। "}</AdminText><button type="button" className="button button-quiet" onClick={() => void references.refetch()}><AdminText>{"আবার খুঁজুন"}</AdminText></button></p>}
    <div className="form-field"><label htmlFor="access-target"><AdminText>{"লক্ষ্য নির্বাচন করুন"}</AdminText></label><select id="access-target" name="target" key={`${kind}:${query}`} required aria-invalid={!!errors?.length} aria-describedby={errors?.length ? "access-target-error" : undefined} disabled={disabled || search !== query || references.isFetching || references.isError} defaultValue="">
      <option value=""><AdminText>{"একটি লক্ষ্য বেছে নিন"}</AdminText></option>{references.data?.entries.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}</select></div>
    {errors?.length ? <p id="access-target-error" role="alert" className="field-error">{errors.join(" ")}</p> : null}
    {!references.isFetching && !references.isError && <p className="muted"><AdminText>{references.data?.pagination.total_count ? "প্রথম ২৪টি ফল দেখানো হচ্ছে। আরও নির্দিষ্ট নাম দিয়ে খুঁজতে পারেন।" : "এই নামে কোনো লক্ষ্য পাওয়া যায়নি।"}</AdminText></p>}
  </fieldset>;
}

"use client";

import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { requestKindle } from "@/api/kindle";
import type { KindleOptions, KindleRequest } from "@/api/types";
import { useUnsavedChanges } from "./unsaved-changes";
import { useUpdateParticipant } from "./update-safety";

export function useKindleForm(options: KindleOptions) {
  const client = useQueryClient();
  const identifier = useRef<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const sending = useMutation({ mutationFn: (values: KindleRequest) => requestKindle(options.book.slug, values), onSuccess: async () => { setDirty(false); await client.invalidateQueries({ queryKey: ["private", "kindle"] }); } });
  useUnsavedChanges(dirty || sending.isPending); useUpdateParticipant({ dirty: sending.isPending });
  function submit(recipients: string[]) {
    identifier.current ??= crypto.randomUUID();
    sending.mutate({ operation_id: identifier.current, expected_updated_at: options.asset_revision, recipients });
  }
  return { sending, submit, markDirty: () => setDirty(true) };
}

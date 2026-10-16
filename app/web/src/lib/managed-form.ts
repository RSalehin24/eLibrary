"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { APIError } from "@/api/http";
import { useUnsavedChanges } from "./unsaved-changes";

export function useManagedForm<Input, Output>(save: (input: Input) => Promise<Output>, onSaved: (output: Output) => Promise<void>) {
  const [dirty, setDirty] = useState(false);
  const saving = useMutation({ mutationFn: save, onSuccess: async (result) => { setDirty(false); await onSaved(result); }, retry: false, gcTime: 0 });
  useUnsavedChanges(dirty || saving.isPending);
  const uncertain = !!saving.error && (!(saving.error instanceof APIError) || saving.error.status !== 400);
  const errors = saving.error instanceof APIError ? saving.error.fieldErrors : {};
  return { saving, dirty, errors, blocked: uncertain || saving.isPending, markDirty: () => setDirty(true), discard: () => { setDirty(false); saving.reset(); } };
}

export function reloadManagedForm() {
  if (window.confirm("বর্তমান তথ্য খুললে সংরক্ষণ না করা লেখা বাদ যাবে। এগোবেন?")) window.location.reload();
}

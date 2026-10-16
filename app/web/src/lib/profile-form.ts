"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { updateProfile } from "@/api/account";
import { APIError } from "@/api/http";
import type { AccountProfile, AccountProfileUpdate } from "@/api/types";
import { useUnsavedChanges } from "./unsaved-changes";
import { useUpdateParticipant } from "./update-safety";

export type ProfileFormProps = { profile: AccountProfile; onSaved: (profile: AccountProfile) => Promise<void> };

export function useProfileForm({ profile, onSaved }: ProfileFormProps) {
  const [dirty, setDirty] = useState(false);
  const saving = useMutation({ mutationFn: (fields: Omit<AccountProfileUpdate, "expected_updated_at">) => updateProfile({ ...fields, expected_updated_at: profile.updated_at }), onSuccess: async (updated) => { setDirty(false); await onSaved(updated); }, retry: false, gcTime: 0 });
  useUnsavedChanges(dirty);
  useUpdateParticipant({ dirty: saving.isPending });
  const errors = saving.error instanceof APIError ? saving.error.fieldErrors : {};
  return { saving, errors, dirty, markDirty: () => setDirty(true), discard: () => { setDirty(false); saving.reset(); } };
}

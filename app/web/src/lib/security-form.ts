"use client";

import { useState } from "react";
import { APIError } from "@/api/http";
import { useUnsavedChanges } from "./unsaved-changes";
import { useUpdateParticipant } from "./update-safety";

export function useSecurityForm(command: { isPending: boolean; error: Error | null }) {
  const [dirty, setDirty] = useState(false);
  useUnsavedChanges(dirty);
  useUpdateParticipant({ dirty: command.isPending });
  return { markDirty: () => setDirty(true), errors: command.error instanceof APIError ? command.error.fieldErrors : {} };
}

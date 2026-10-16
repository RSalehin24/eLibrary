"use client";

import { useEffect } from "react";
import { useUpdateParticipant } from "./update-safety";

export function useUnsavedChanges(dirty: boolean) {
  useUpdateParticipant({ dirty });
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
}

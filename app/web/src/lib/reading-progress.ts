"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { saveReadingProgress } from "@/api/reading";
import type { ReaderProgress } from "@/api/types";
import { ProgressWriter, type SaveStatus } from "./progress-writer";
import { useUnsavedChanges } from "./unsaved-changes";
import { useUpdateParticipant } from "./update-safety";

const SAVE_DELAY_MS = 2_000;
const SAVE_INTERVAL_MS = 15_000;

export function useReadingProgress(identifier: string, capture: () => ReaderProgress) {
  const [status, setStatus] = useState<SaveStatus>("saved");
  const [writer] = useState(() => new ProgressWriter((progress) => saveReadingProgress(identifier, progress), setStatus));
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef<ReaderProgress | null>(null);
  const enqueue = useCallback((progress: ReaderProgress) => {
    if (latest.current?.last_location === progress.last_location && latest.current.progress_percent === progress.progress_percent) return;
    latest.current = progress; writer.enqueue(progress);
  }, [writer]);
  const currentCapture = useRef(capture);
  useEffect(() => { currentCapture.current = capture; }, [capture]);
  const flush = useCallback(() => { enqueue(currentCapture.current()); return writer.flush(); }, [writer, enqueue]);
  useUpdateParticipant({ dirty: false, prepare: flush });
  const queue = useCallback((progress: ReaderProgress) => {
    enqueue(progress);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => { if (!writer.hasFailed) void flush(); }, SAVE_DELAY_MS);
  }, [enqueue, flush, writer]);
  useEffect(() => {
    const interval = setInterval(() => { if (!writer.hasFailed) void flush(); }, SAVE_INTERVAL_MS);
    window.addEventListener("beforeunload", flush);
    return () => { clearInterval(interval); if (timer.current) clearTimeout(timer.current);
      window.removeEventListener("beforeunload", flush); void flush(); };
  }, [flush, writer]);
  useUnsavedChanges(status === "failed");
  return { queue, status, flush };
}

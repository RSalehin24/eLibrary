import { useEffect, useRef, useState } from "react";
import { resolveProcessingStreamUrl } from "../api";

export function useProcessingStream({
  applyProcessingVersions,
  canLoadProcessingState,
  loadProcessingState,
  onProcessingPage,
  processingPage,
  queueProcessingStateReload
}) {
  const [streamMode, setStreamMode] = useState("idle");
  const eventSourceRef = useRef(null);

  useEffect(() => {
    if (
      !onProcessingPage ||
      !canLoadProcessingState ||
      typeof window === "undefined"
    ) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setStreamMode("idle");
      return undefined;
    }

    if (typeof EventSource === "undefined") {
      setStreamMode("unsupported");
      return undefined;
    }

    let disposed = false;
    const nextSource = new EventSource(
      resolveProcessingStreamUrl(
        `/processing/stream/?page=${encodeURIComponent(processingPage)}`
      ),
      { withCredentials: true }
    );
    eventSourceRef.current = nextSource;
    setStreamMode("connecting");

    const handlePayload = (event) => {
      if (disposed || eventSourceRef.current !== nextSource) return;
      try {
        const payload = JSON.parse(event.data || "{}");
        const versionUpdate = applyProcessingVersions(payload.versions || {});
        if (versionUpdate.sharedChanged) {
          queueProcessingStateReload();
        }
      } catch {}
    };

    nextSource.addEventListener("connected", () => {
      if (disposed || eventSourceRef.current !== nextSource) return;
      setStreamMode("connected");
    });
    nextSource.addEventListener("versions", handlePayload);
    nextSource.onerror = () => {
      if (disposed || eventSourceRef.current !== nextSource) return;
      setStreamMode("reconnecting");
    };

    return () => {
      disposed = true;
      if (eventSourceRef.current === nextSource) {
        nextSource.close();
        eventSourceRef.current = null;
      }
      setStreamMode("idle");
    };
  }, [
    applyProcessingVersions,
    canLoadProcessingState,
    onProcessingPage,
    processingPage,
    queueProcessingStateReload
  ]);

  useEffect(() => {
    if (
      !onProcessingPage ||
      !canLoadProcessingState ||
      !["reconnecting", "unsupported"].includes(streamMode) ||
      typeof window === "undefined"
    ) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      loadProcessingState();
    }, 15000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [canLoadProcessingState, loadProcessingState, onProcessingPage, streamMode]);

  useEffect(() => {
    if (canLoadProcessingState) return undefined;
    setStreamMode("idle");
    return undefined;
  }, [canLoadProcessingState]);

  return streamMode;
}

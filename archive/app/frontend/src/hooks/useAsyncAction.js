import { useCallback, useRef, useState } from "react";

export function useAsyncAction() {
  const [pendingKey, setPendingKey] = useState("");
  const pendingRef = useRef("");

  const run = useCallback(
    async (key, action) => {
      if (pendingRef.current) {
        return null;
      }
      pendingRef.current = key;
      setPendingKey(key);
      try {
        return await action();
      } finally {
        pendingRef.current = "";
        setPendingKey("");
      }
    },
    [],
  );

  return {
    pendingKey,
    pending: Boolean(pendingKey),
    run,
  };
}

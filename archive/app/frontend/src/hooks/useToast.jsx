import { createContext, useContext, useEffect, useMemo, useState } from "react";
import ToastViewport from "../components/ToastViewport";
import {
  createNotificationSoundPlayer,
  readNotificationSoundMuted,
  writeNotificationSoundMuted,
} from "../utils/notificationAudio";
import { createToastManager } from "../utils/toastManager";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [manager] = useState(() =>
    createToastManager({
      initialMuted: readNotificationSoundMuted(globalThis?.localStorage),
      playSound: createNotificationSoundPlayer(),
    }),
  );
  const [snapshot, setSnapshot] = useState(() => manager.getState());

  useEffect(() => manager.subscribe(setSnapshot), [manager]);

  useEffect(() => {
    writeNotificationSoundMuted(globalThis?.localStorage, snapshot.muted);
  }, [snapshot.muted]);

  useEffect(
    () => () => {
      manager.destroy();
    },
    [manager],
  );

  const value = useMemo(() => {
    // Auto-dedupe consecutive toasts that share the same title+type within
    // the manager's holdOpen window. Callers may still pass an explicit
    // `groupKey` to opt-into stronger grouping (e.g. background polling).
    function pushWithDedupe(input, fallbackType) {
      if (typeof input === "string") {
        return manager.push(
          { description: input, groupKey: `${fallbackType}:${input}` },
          fallbackType,
        );
      }
      if (input && typeof input === "object" && !input.groupKey) {
        const title = (input.title || input.message || "").toString().trim();
        const description = (input.description || "").toString().trim();
        const seed = `${input.type || fallbackType}:${title || description}`;
        if (title || description) {
          return manager.push({ ...input, groupKey: seed }, fallbackType);
        }
      }
      return manager.push(input, fallbackType);
    }

    return {
      show: (input) => pushWithDedupe(input, "info"),
      info: (input) => pushWithDedupe(input, "info"),
      success: (input) => pushWithDedupe(input, "success"),
      error: (input) => pushWithDedupe(input, "error"),
      dismiss: manager.dismiss,
      muted: snapshot.muted,
      setMuted: (value) => manager.setMuted(value),
      toggleMuted: () => manager.toggleMuted(),
    };
  }, [manager, snapshot.muted]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport toasts={snapshot.toasts} onDismiss={manager.dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}

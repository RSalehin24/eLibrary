"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { browserPreferenceStorage, createNotificationPreferences, NOTIFICATION_SOUND_STORAGE_KEY } from "@/lib/notification-preference";
import { createNotificationSoundPlayer, type NotificationKind } from "@/lib/notification-sound";
import { useSiteLanguage } from "./site-language";
import { Icon } from "./icon";

type Notification = { id: number; kind: NotificationKind; message: string };
type Notifications = {
  enabled: boolean; persistent: boolean; setEnabled: (value: boolean) => void;
  show: (message: string, kind?: NotificationKind) => void;
  sound: (kind: NotificationKind) => void;
};
const NotificationContext = createContext<Notifications | null>(null);
const serverPreference = () => false;

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [preferences] = useState(() => createNotificationPreferences(browserPreferenceStorage));
  const [player] = useState(() => createNotificationSoundPlayer());
  const enabled = useSyncExternalStore(preferences.subscribe, preferences.getSnapshot, serverPreference);
  const [notification, setNotification] = useState<Notification | null>(null);
  const previous = useRef({ message: "", kind: "info", at: 0 });
  const { language } = useSiteLanguage();
  useEffect(() => {
    preferences.load();
    const changed = (event: StorageEvent) => { if (event.key === NOTIFICATION_SOUND_STORAGE_KEY || event.key === null) preferences.load(); };
    window.addEventListener("storage", changed);
    return () => { window.removeEventListener("storage", changed); void player.dispose(); };
  }, [preferences, player]);
  useEffect(() => {
    player.setEnabled(enabled);
    if (!enabled) return;
    const unlock = () => { void player.unlock(); };
    window.addEventListener("pointerdown", unlock, { once: true, capture: true });
    window.addEventListener("keydown", unlock, { once: true, capture: true });
    return () => { window.removeEventListener("pointerdown", unlock, true); window.removeEventListener("keydown", unlock, true); };
  }, [enabled, player]);
  const sound = useCallback((kind: NotificationKind) => { player.play(kind); }, [player]);
  const show = useCallback((message: string, kind: NotificationKind = "success") => {
    const now = Date.now();
    if (previous.current.message === message && previous.current.kind === kind && now - previous.current.at < 1500) return;
    previous.current = { message, kind, at: now };
    setNotification({ id: now, message, kind }); sound(kind);
  }, [sound]);
  function setEnabled(value: boolean) {
    player.setEnabled(value);
    if (value) void player.unlock();
    preferences.save(value);
  }
  return <NotificationContext.Provider value={{ enabled, persistent: preferences.getPersistent(), setEnabled, show, sound }}>
    {children}
    <div className="notification-viewport" data-testid="notifications" role="region" aria-label={language === "bn" ? "অনুরোধের ফলাফল" : "Request results"}>
      <div role={notification && notification.kind !== "error" ? "status" : undefined} aria-live="polite" aria-atomic="true">{notification && notification.kind !== "error" && <NotificationCard notification={notification} dismiss={() => setNotification(null)} />}</div>
      <div role={notification?.kind === "error" ? "alert" : undefined} aria-live="assertive" aria-atomic="true">{notification?.kind === "error" && <NotificationCard notification={notification} dismiss={() => setNotification(null)} />}</div>
    </div>
  </NotificationContext.Provider>;
}

function NotificationCard({ notification, dismiss }: { notification: Notification; dismiss: () => void }) {
  const { t, language } = useSiteLanguage();
  return <div className={`notification-card notification-${notification.kind}`} key={notification.id}>
    <Icon name={notification.kind === "success" ? "check" : notification.kind === "error" ? "warning" : "help"} />
    <p>{t(notification.message)}</p><button type="button" className="button button-quiet" aria-label={language === "bn" ? "বার্তা বন্ধ করুন" : "Dismiss notification"} onClick={dismiss}>×</button>
  </div>;
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) throw new Error("Notifications require NotificationProvider.");
  return context;
}

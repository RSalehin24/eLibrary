export const NOTIFICATION_SOUND_STORAGE_KEY = "library.notification-sounds";
type PreferenceStorage = Pick<Storage, "getItem" | "setItem">;

export function readNotificationSounds(storage?: PreferenceStorage) {
  try { return storage?.getItem(NOTIFICATION_SOUND_STORAGE_KEY) === "1"; }
  catch { return false; }
}

export function writeNotificationSounds(storage: PreferenceStorage | undefined, enabled: boolean) {
  if (!storage) return false;
  try { storage.setItem(NOTIFICATION_SOUND_STORAGE_KEY, enabled ? "1" : "0"); return true; }
  catch { return false; }
}

export function browserPreferenceStorage() {
  try { return window.localStorage; } catch { return undefined; }
}

export function createNotificationPreferences(storage: () => PreferenceStorage | undefined) {
  let enabled = false;
  let persistent = true;
  const listeners = new Set<() => void>();
  function publish(next: boolean) { enabled = next; listeners.forEach((listener) => listener()); }
  return {
    getSnapshot: () => enabled,
    getPersistent: () => persistent,
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    load() { publish(readNotificationSounds(storage())); },
    save(next: boolean) { persistent = writeNotificationSounds(storage(), next); publish(next); },
  };
}

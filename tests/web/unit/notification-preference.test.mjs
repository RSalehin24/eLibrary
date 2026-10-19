import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { createNotificationPreferences, readNotificationSounds, writeNotificationSounds, NOTIFICATION_SOUND_STORAGE_KEY } = await typescriptModule(new URL("../../../app/web/src/lib/notification-preference.ts", import.meta.url));

test("only an explicit stored opt-in enables sounds", () => {
  for (const value of [null, "", "0", "true", "unexpected"]) {
    assert.equal(readNotificationSounds({ getItem() { return value; } }), false);
  }
  assert.equal(readNotificationSounds({ getItem() { return "1"; } }), true);
  assert.equal(readNotificationSounds(), false);
  assert.equal(readNotificationSounds({ getItem() { throw new Error("Storage blocked"); } }), false);
});

test("legacy mute choices stay silent until a new explicit opt-in", () => {
  const legacyKey = "app.notifications.muted";
  for (const muted of ["1", "0"]) {
    const values = new Map([[legacyKey, muted]]);
    const storage = { getItem(key) { return values.get(key) ?? null; }, setItem(key, value) { values.set(key, value); } };
    assert.equal(readNotificationSounds(storage), false);
    assert.equal(writeNotificationSounds(storage, true), true);
    assert.equal(readNotificationSounds(storage), true);
    assert.equal(values.get(legacyKey), muted);
  }
});

test("the preference persists across instances and synchronizes external changes without initial autoplay", () => {
  const values = new Map();
  const storage = { getItem(key) { return values.get(key) ?? null; }, setItem(key, value) { values.set(key, value); } };
  const first = createNotificationPreferences(() => storage);
  let events = 0;
  const unsubscribe = first.subscribe(() => { events += 1; });
  assert.equal(first.getSnapshot(), false);
  first.save(true);
  assert.equal(values.get(NOTIFICATION_SOUND_STORAGE_KEY), "1");
  assert.equal(first.getSnapshot(), true);
  assert.equal(first.getPersistent(), true);
  const second = createNotificationPreferences(() => storage);
  assert.equal(second.getSnapshot(), false);
  second.load();
  assert.equal(second.getSnapshot(), true);
  second.save(false);
  first.load();
  assert.equal(first.getSnapshot(), false);
  assert.equal(events, 2);
  unsubscribe();
  first.save(true);
  assert.equal(events, 2);
});

test("blocked persistent storage retains a usable session preference and reports its limitation", () => {
  const storage = { getItem() { return null; }, setItem() { throw new Error("Storage denied"); } };
  assert.equal(writeNotificationSounds(undefined, true), false);
  assert.equal(writeNotificationSounds(storage, true), false);
  const preferences = createNotificationPreferences(() => storage);
  preferences.save(true);
  assert.equal(preferences.getSnapshot(), true);
  assert.equal(preferences.getPersistent(), false);
});

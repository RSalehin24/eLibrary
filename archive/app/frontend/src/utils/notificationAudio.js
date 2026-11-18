export const NOTIFICATION_SOUND_STORAGE_KEY = "app.notifications.muted";

export const SOUND_PRESETS = {
  success: [
    { frequency: 660, duration: 0.08, wave: "sine", gain: 0.042, offset: 0 },
    { frequency: 880, duration: 0.12, wave: "sine", gain: 0.032, offset: 0.08 },
  ],
  error: [
    {
      frequency: 260,
      duration: 0.18,
      wave: "triangle",
      gain: 0.06,
      offset: 0,
    },
    {
      frequency: 196,
      duration: 0.16,
      wave: "triangle",
      gain: 0.048,
      offset: 0.11,
    },
  ],
  info: [
    { frequency: 420, duration: 0.08, wave: "sine", gain: 0.034, offset: 0 },
    { frequency: 560, duration: 0.12, wave: "sine", gain: 0.028, offset: 0.08 },
  ],
};

function storageCall(storage, method, ...args) {
  if (!storage || typeof storage[method] !== "function") {
    return null;
  }
  try {
    return storage[method](...args);
  } catch {
    return null;
  }
}

export function readNotificationSoundMuted(storage) {
  return storageCall(storage, "getItem", NOTIFICATION_SOUND_STORAGE_KEY) === "1";
}

export function writeNotificationSoundMuted(storage, muted) {
  storageCall(
    storage,
    "setItem",
    NOTIFICATION_SOUND_STORAGE_KEY,
    muted ? "1" : "0",
  );
}

export function createNotificationSoundPlayer({
  AudioContextClass = globalThis.AudioContext || globalThis.webkitAudioContext,
} = {}) {
  let context = null;

  function ensureContext() {
    if (!AudioContextClass) {
      return null;
    }
    if (!context) {
      context = new AudioContextClass();
    }
    if (context.state === "suspended" && typeof context.resume === "function") {
      return context;
    }
    return context;
  }

  function emitTones(audioContext, tones) {
    const baseTime = Number.isFinite(audioContext.currentTime)
      ? audioContext.currentTime
      : 0;

    tones.forEach((tone) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      const startTime = baseTime + tone.offset;
      const peakTime = startTime + Math.min(tone.duration / 3, 0.02);
      const stopTime = startTime + tone.duration;

      oscillator.type = tone.wave;
      oscillator.frequency.setValueAtTime(tone.frequency, startTime);

      gainNode.gain.setValueAtTime(0.0001, startTime);
      gainNode.gain.linearRampToValueAtTime(tone.gain, peakTime);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, stopTime);

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.start(startTime);
      oscillator.stop(stopTime);
    });
  }

  return function playNotificationSound(type = "info") {
    const audioContext = ensureContext();
    if (
      !audioContext ||
      typeof audioContext.createOscillator !== "function" ||
      typeof audioContext.createGain !== "function"
    ) {
      return false;
    }

    const tones = SOUND_PRESETS[type] || SOUND_PRESETS.info;

    try {
      if (
        audioContext.state === "suspended" &&
        typeof audioContext.resume === "function"
      ) {
        const resumed = Promise.resolve(audioContext.resume());
        if (audioContext.state === "running") {
          emitTones(audioContext, tones);
          return true;
        }
        resumed.then(() => emitTones(audioContext, tones)).catch(() => {});
        return true;
      }

      emitTones(audioContext, tones);
      return true;
    } catch {
      return false;
    }
  };
}

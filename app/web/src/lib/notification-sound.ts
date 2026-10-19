export type NotificationKind = "success" | "error" | "info";

const tones: Record<NotificationKind, readonly number[]> = {
  success: [660, 880], error: [260, 196], info: [420, 560],
};

function emitTones(context: AudioContext, kind: NotificationKind) {
  tones[kind].forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const start = context.currentTime + index * 0.09;
    oscillator.type = kind === "error" ? "triangle" : "sine";
    oscillator.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.linearRampToValueAtTime(0.035, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.12);
    oscillator.connect(gain); gain.connect(context.destination);
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
    oscillator.start(start); oscillator.stop(start + 0.12);
  });
}

export function createNotificationSoundPlayer(factory: () => AudioContext | undefined = () => {
  const Constructor = globalThis.AudioContext;
  return Constructor ? new Constructor() : undefined;
}) {
  let enabled = false;
  let context: AudioContext | undefined;
  let ready = false;
  return {
    setEnabled(value: boolean) { enabled = value; },
    async unlock() {
      if (!enabled) return false;
      try {
        context ??= factory();
        if (!context) return false;
        if (context.state === "suspended") await context.resume();
        ready = context.state === "running";
        return ready;
      } catch { return false; }
    },
    play(kind: NotificationKind) {
      if (!enabled || !ready || !context || context.state !== "running") return false;
      try { emitTones(context, kind); return true; } catch { return false; }
    },
    async dispose() {
      ready = false;
      if (!context || context.state === "closed") return;
      try { await context.close(); } catch { return; }
    },
  };
}

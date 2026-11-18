import assert from "node:assert/strict";
import test from "node:test";

import {
  createNotificationSoundPlayer,
  readNotificationSoundMuted,
  writeNotificationSoundMuted,
} from "../../../app/frontend/src/utils/notificationAudio.js";

function buildFakeAudioContext() {
  const started = [];
  let lastInstance = null;

  class FakeGainNode {
    constructor() {
      this.gain = {
        setValueAtTime() {},
        linearRampToValueAtTime() {},
        exponentialRampToValueAtTime() {},
      };
    }

    connect() {}
  }

  class FakeOscillatorNode {
    constructor() {
      this.type = "sine";
      this.frequencyValue = 0;
      this.frequency = {
        setValueAtTime: (value) => {
          this.frequencyValue = value;
        },
      };
    }

    connect() {}

    start(startTime) {
      started.push({
        frequency: this.frequencyValue,
        startTime,
        type: this.type,
      });
    }

    stop() {}
  }

  class FakeAudioContext {
    constructor() {
      this.currentTime = 1.5;
      this.destination = {};
      this.state = "suspended";
      this.resumeCalls = 0;
      lastInstance = this;
    }

    createOscillator() {
      return new FakeOscillatorNode();
    }

    createGain() {
      return new FakeGainNode();
    }

    resume() {
      this.resumeCalls += 1;
      this.state = "running";
      return Promise.resolve();
    }
  }

  return {
    FakeAudioContext,
    getLastInstance: () => lastInstance,
    started,
  };
}

test("notification audio uses distinct sound presets by toast type", async () => {
  const fakeAudio = buildFakeAudioContext();
  const playSound = createNotificationSoundPlayer({
    AudioContextClass: fakeAudio.FakeAudioContext,
  });

  assert.equal(playSound("success"), true);
  assert.equal(playSound("error"), true);
  assert.equal(playSound("info"), true);
  assert.equal(fakeAudio.getLastInstance().resumeCalls, 1);
  await Promise.resolve();

  assert.deepEqual(
    fakeAudio.started.slice(0, 2).map((tone) => tone.frequency),
    [660, 880],
  );
  assert.deepEqual(
    fakeAudio.started.slice(2, 4).map((tone) => tone.frequency),
    [260, 196],
  );
  assert.deepEqual(
    fakeAudio.started.slice(4, 6).map((tone) => tone.frequency),
    [420, 560],
  );
});

test("notification mute preference persists to storage", () => {
  const storage = new Map();
  const storageApi = {
    getItem(key) {
      return storage.has(key) ? storage.get(key) : null;
    },
    setItem(key, value) {
      storage.set(key, value);
    },
  };

  assert.equal(readNotificationSoundMuted(storageApi), false);
  writeNotificationSoundMuted(storageApi, true);
  assert.equal(readNotificationSoundMuted(storageApi), true);
  writeNotificationSoundMuted(storageApi, false);
  assert.equal(readNotificationSoundMuted(storageApi), false);
});

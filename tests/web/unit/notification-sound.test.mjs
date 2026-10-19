import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { createNotificationSoundPlayer } = await typescriptModule(new URL("../../../app/web/src/lib/notification-sound.ts", import.meta.url));

function audioFixture() {
  const state = { created: 0, started: [], closed: 0 };
  const context = {
    state: "suspended", currentTime: 2, destination: {},
    async resume() { this.state = "running"; },
    async close() { this.state = "closed"; state.closed += 1; },
    createOscillator() {
      let frequency = 0;
      return { frequency: { setValueAtTime(value) { frequency = value; } }, connect() {}, disconnect() {},
        start() { state.started.push(frequency); }, stop() {} };
    },
    createGain() { return { gain: { setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {}, disconnect() {} }; },
  };
  const player = createNotificationSoundPlayer(() => { state.created += 1; return context; });
  return { player, state, context };
}

test("sounds are muted initially and never create an audio context or autoplay before explicit activation", async () => {
  const { player, state } = audioFixture();
  assert.equal(player.play("success"), false);
  assert.equal(await player.unlock(), false);
  assert.equal(state.created, 0);
  player.setEnabled(true);
  assert.equal(player.play("success"), false);
  assert.equal(state.created, 0);
  assert.deepEqual(state.started, []);
});

test("explicitly activated sounds distinguish successful and failed requests and stop when disabled", async () => {
  const { player, state } = audioFixture();
  player.setEnabled(true);
  assert.equal(await player.unlock(), true);
  assert.deepEqual(state.started, []);
  assert.equal(player.play("success"), true);
  assert.equal(player.play("error"), true);
  assert.deepEqual(state.started, [660, 880, 260, 196]);
  assert.equal(state.created, 1);
  player.setEnabled(false);
  assert.equal(player.play("success"), false);
  assert.equal(state.started.length, 4);
  await player.dispose();
  assert.equal(state.closed, 1);
});

test("browser audio restrictions and unavailable audio keep request feedback usable", async () => {
  const { player, context, state } = audioFixture();
  context.resume = async () => { throw new Error("Autoplay is blocked"); };
  player.setEnabled(true);
  assert.equal(await player.unlock(), false);
  assert.equal(player.play("error"), false);
  assert.deepEqual(state.started, []);
  const unavailable = createNotificationSoundPlayer(() => undefined);
  unavailable.setEnabled(true);
  assert.equal(await unavailable.unlock(), false);
  assert.equal(unavailable.play("success"), false);
});

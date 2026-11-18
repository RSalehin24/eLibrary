import { expect } from "../support/playwright";
import { card } from "./bootHelpers.js";
export function checkbox(page, pageId, cardId, id) {
  return page.getByTestId(`${pageId}-${cardId}-select-${id}`);
}
export async function automationControlHeights(page, pageId) {
  return page.evaluate(targetPageId => {
    const runButton = document.querySelector(`[data-testid="${targetPageId}-automation-run-btn"]`);
    const toggle = document.querySelector(`[data-testid="${targetPageId}-automation-enabled"]`)?.closest(".processing-switch");
    if (!runButton || !toggle) {
      return null;
    }
    return {
      button: Math.round(runButton.getBoundingClientRect().height),
      toggle: Math.round(toggle.getBoundingClientRect().height)
    };
  }, pageId);
}
export async function controlDimensions(page, controls) {
  return page.evaluate(items => {
    return Object.fromEntries(items.map(({
      key,
      testId,
      selector,
      closest
    }) => {
      const element = selector ? document.querySelector(selector) : document.querySelector(`[data-testid="${testId}"]`);
      const target = closest ? element?.closest(closest) : element;
      if (!target) {
        return [key, null];
      }
      const rect = target.getBoundingClientRect();
      return [key, {
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      }];
    }));
  }, controls);
}
export async function openCardFilters(page, pageId, cardId) {
  await card(page, pageId, cardId).getByRole("button", {
    name: /^Filters/
  }).click();
}
export async function installNotificationAudioSpy(page) {
  await page.addInitScript(() => {
    const events = [];
    window.__notificationSoundEvents = events;
    class FakeGainNode {
      constructor() {
        this.gain = {
          setValueAtTime() {},
          linearRampToValueAtTime() {},
          exponentialRampToValueAtTime() {}
        };
      }
      connect() {}
    }
    class FakeOscillatorNode {
      constructor() {
        this.type = "sine";
        this.frequencyValue = 0;
        this.frequency = {
          setValueAtTime: value => {
            this.frequencyValue = value;
          }
        };
      }
      connect() {}
      start(startTime = 0) {
        events.push({
          frequency: this.frequencyValue,
          startTime,
          type: this.type
        });
      }
      stop() {}
    }
    class FakeAudioContext {
      constructor() {
        this.currentTime = 0;
        this.destination = {};
        this.state = "running";
      }
      createOscillator() {
        return new FakeOscillatorNode();
      }
      createGain() {
        return new FakeGainNode();
      }
      resume() {
        return Promise.resolve();
      }
    }
    window.AudioContext = FakeAudioContext;
    window.webkitAudioContext = FakeAudioContext;
  });
}
export async function notificationSoundEventCount(page) {
  return page.evaluate(() => (window.__notificationSoundEvents || []).length);
}
export async function expectVisibleCount(page, pageId, cardId, count) {
  await expect(page.getByTestId(`${pageId}-${cardId}-count`)).toContainText(`${count}`);
}

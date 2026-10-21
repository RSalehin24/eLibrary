import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { activateReaderTool } = await typescriptModule(new URL("../../../app/web/src/lib/reader-shortcuts.ts", import.meta.url));

test("reader tools open from either document without requiring visible fullscreen buttons", () => {
  for (const [key, tool] of [["t", "contents"], ["s", "settings"], ["/", "search"]]) {
    let clicked = 0, prevented = 0;
    activateReaderTool({ key, preventDefault: () => prevented++ }, { querySelector: selector => {
      assert.equal(selector, `[data-reader-tool="${tool}"]`);
      return { click: () => clicked++ };
    } });
    assert.equal(clicked, 1); assert.equal(prevented, 1);
  }
});

test("reader tool keys preserve editing, modifiers, media controls and unavailable tools", () => {
  const fail = () => assert.fail("The shortcut must not run");
  for (const event of [{ key: "t", ctrlKey: true }, { key: "s", metaKey: true }, { key: "/", altKey: true }, { key: "t", shiftKey: true }, { key: "s", repeat: true }, { key: "t", defaultPrevented: true }, { key: "t", target: { closest: () => ({}) } }]) {
    activateReaderTool({ ...event, preventDefault: fail }, { querySelector: fail });
  }
  activateReaderTool({ key: "/", preventDefault: fail }, { querySelector: () => null });
  activateReaderTool({ key: "t", preventDefault: fail }, null);
});

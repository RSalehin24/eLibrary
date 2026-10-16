import assert from "node:assert/strict";
import test from "node:test";
import { normalizeToken, getFilteredSuggestions, handleKeyDown, makeState, simulateBlur } from '../support/tag-input-state.js';


// ---------------------------------------------------------------------------
// 1. Arrow-Down navigation
// ---------------------------------------------------------------------------

test("ArrowDown moves highlightedIndex from -1 to 0", () => {
  const state = makeState({ inputValue: "" });
  const next = handleKeyDown(state, "ArrowDown");
  assert.equal(next.highlightedIndex, 0);
});


test("ArrowDown advances highlightedIndex step by step", () => {
  let state = makeState({ inputValue: "" });
  state = handleKeyDown(state, "ArrowDown"); // 0
  state = handleKeyDown(state, "ArrowDown"); // 1
  state = handleKeyDown(state, "ArrowDown"); // 2
  assert.equal(state.highlightedIndex, 2);
});


test("ArrowDown wraps around to 0 after the last suggestion", () => {
  // suggestions are capped at 6, so last index is 5
  const state = makeState({ highlightedIndex: 5 });
  const next = handleKeyDown(state, "ArrowDown");
  assert.equal(next.highlightedIndex, 0);
});


// ---------------------------------------------------------------------------
// 2. Arrow-Up navigation
// ---------------------------------------------------------------------------

test("ArrowUp from -1 jumps to the last suggestion", () => {
  const state = makeState({ inputValue: "" });
  const next = handleKeyDown(state, "ArrowUp");
  const filteredCount = getFilteredSuggestions(state.suggestions, state.values, state.inputValue).length;
  assert.equal(next.highlightedIndex, filteredCount - 1);
});


test("ArrowUp decrements highlightedIndex", () => {
  const state = makeState({ highlightedIndex: 3 });
  const next = handleKeyDown(state, "ArrowUp");
  assert.equal(next.highlightedIndex, 2);
});


test("ArrowUp wraps from index 0 to the last suggestion", () => {
  const state = makeState({ highlightedIndex: 0 });
  const next = handleKeyDown(state, "ArrowUp");
  const filteredCount = getFilteredSuggestions(state.suggestions, state.values, state.inputValue).length;
  assert.equal(next.highlightedIndex, filteredCount - 1);
});


// ---------------------------------------------------------------------------
// 3. Tab key — select suggestion
// ---------------------------------------------------------------------------

test("Tab selects the highlighted suggestion", () => {
  const state = makeState({ highlightedIndex: 2 }); // 'Carol'
  const next = handleKeyDown(state, "Tab");
  assert.ok(next.values.includes("Carol"));
  assert.equal(next.inputValue, "");
  assert.equal(next.highlightedIndex, -1);
});


test("Tab selects the first suggestion when nothing is highlighted", () => {
  const state = makeState({ highlightedIndex: -1 });
  const next = handleKeyDown(state, "Tab");
  assert.ok(next.values.includes("Alice")); // first suggestion
});


test("Tab clears inputValue after selection", () => {
  const state = makeState({ inputValue: "Ali", highlightedIndex: 0 });
  const next = handleKeyDown(state, "Tab");
  assert.equal(next.inputValue, "");
});


// ---------------------------------------------------------------------------
// 4. Enter / comma — confirm selection or free-text
// ---------------------------------------------------------------------------

test("Enter confirms the highlighted suggestion", () => {
  const state = makeState({ highlightedIndex: 1 }); // 'Bob'
  const next = handleKeyDown(state, "Enter");
  assert.ok(next.values.includes("Bob"));
});


test("Comma confirms the highlighted suggestion", () => {
  const state = makeState({ highlightedIndex: 1 });
  const next = handleKeyDown(state, ",");
  assert.ok(next.values.includes("Bob"));
});


test("Enter adds free-text when no suggestion is highlighted", () => {
  const state = makeState({ inputValue: "Zara", highlightedIndex: -1, suggestions: [] });
  const next = handleKeyDown(state, "Enter");
  assert.ok(next.values.includes("Zara"));
});


test("Enter ignores empty inputValue when no suggestion is highlighted", () => {
  const state = makeState({ inputValue: "", highlightedIndex: -1, suggestions: [] });
  const next = handleKeyDown(state, "Enter");
  assert.deepEqual(next.values, []);
});


// ---------------------------------------------------------------------------
// 5. Escape — close dropdown
// ---------------------------------------------------------------------------

test("Escape closes the dropdown and resets highlightedIndex", () => {
  const state = makeState({ highlightedIndex: 2 });
  const next = handleKeyDown(state, "Escape");
  assert.equal(next.highlightedIndex, -1);
  assert.equal(next.focused, false);
});


test("Escape has no effect when there are no suggestions", () => {
  const state = makeState({ suggestions: [], highlightedIndex: -1, focused: true });
  const next = handleKeyDown(state, "Escape");
  assert.equal(next.focused, true); // unchanged
});


// ---------------------------------------------------------------------------
// 6. Backspace — remove last tag
// ---------------------------------------------------------------------------

test("Backspace removes the last tag when input is empty", () => {
  const state = makeState({ values: ["Alice", "Bob"], inputValue: "" });
  const next = handleKeyDown(state, "Backspace");
  assert.deepEqual(next.values, ["Alice"]);
});


test("Backspace does nothing when input has text", () => {
  const state = makeState({ values: ["Alice"], inputValue: "Bo" });
  const next = handleKeyDown(state, "Backspace");
  assert.deepEqual(next.values, ["Alice"]);
});


test("Backspace does nothing when values list is empty", () => {
  const state = makeState({ values: [], inputValue: "" });
  const next = handleKeyDown(state, "Backspace");
  assert.deepEqual(next.values, []);
});


// ---------------------------------------------------------------------------
// 7. ArrowLeft / ArrowRight — field navigation
// ---------------------------------------------------------------------------

test("ArrowLeft calls onArrowLeft when input is empty", () => {
  let called = false;
  const state = makeState({ inputValue: "", suggestions: [] });
  handleKeyDown(state, "ArrowLeft", { onArrowLeft: () => { called = true; } });
  assert.ok(called, "onArrowLeft should have been called");
});


test("ArrowLeft does NOT call onArrowLeft when input has text", () => {
  let called = false;
  const state = makeState({ inputValue: "Alic", suggestions: [] });
  handleKeyDown(state, "ArrowLeft", { onArrowLeft: () => { called = true; } });
  assert.ok(!called, "onArrowLeft should NOT be called while typing");
});


test("ArrowRight calls onArrowRight when input is empty", () => {
  let called = false;
  const state = makeState({ inputValue: "", suggestions: [] });
  handleKeyDown(state, "ArrowRight", { onArrowRight: () => { called = true; } });
  assert.ok(called, "onArrowRight should have been called");
});


test("ArrowRight does NOT call onArrowRight when input has text", () => {
  let called = false;
  const state = makeState({ inputValue: "Bo", suggestions: [] });
  handleKeyDown(state, "ArrowRight", { onArrowRight: () => { called = true; } });
  assert.ok(!called);
});


test("ArrowLeft/Right state is unchanged after navigation callback", () => {
  const state = makeState({ inputValue: "", suggestions: [] });
  const next = handleKeyDown(state, "ArrowLeft", { onArrowLeft: () => {} });
  assert.deepEqual(next.values, state.values);
  assert.equal(next.highlightedIndex, state.highlightedIndex);
});


// ArrowDown/ArrowUp should NOT trigger field navigation even on empty input
test("ArrowDown does not fire onArrowLeft/Right when suggestions are present", () => {
  let leftCalled = false;
  let rightCalled = false;
  const state = makeState({ inputValue: "" });
  handleKeyDown(state, "ArrowDown", {
    onArrowLeft: () => { leftCalled = true; },
    onArrowRight: () => { rightCalled = true; },
  });
  assert.ok(!leftCalled && !rightCalled);
});

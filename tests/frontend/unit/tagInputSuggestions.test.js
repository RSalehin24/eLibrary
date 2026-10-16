import assert from "node:assert/strict";
import test from "node:test";
import { normalizeToken, getFilteredSuggestions, handleKeyDown, makeState, simulateBlur } from '../support/tag-input-state.js';


// ---------------------------------------------------------------------------
// 8. Suggestion filtering
// ---------------------------------------------------------------------------

test("getFilteredSuggestions returns all items when inputValue is empty", () => {
  const suggestions = ["Alice", "Bob", "Carol"];
  const result = getFilteredSuggestions(suggestions, [], "");
  assert.deepEqual(result, ["Alice", "Bob", "Carol"]);
});


test("getFilteredSuggestions filters by inputValue case-insensitively", () => {
  const suggestions = ["Alice", "Bob", "Carol"];
  const result = getFilteredSuggestions(suggestions, [], "ali");
  assert.deepEqual(result, ["Alice"]);
});


test("getFilteredSuggestions excludes already-selected values", () => {
  const suggestions = ["Alice", "Bob", "Carol"];
  const result = getFilteredSuggestions(suggestions, ["Alice"], "");
  assert.deepEqual(result, ["Bob", "Carol"]);
});


test("getFilteredSuggestions excludes already-selected values case-insensitively", () => {
  const suggestions = ["Alice", "Bob"];
  const result = getFilteredSuggestions(suggestions, ["alice"], "");
  assert.deepEqual(result, ["Bob"]);
});


test("getFilteredSuggestions caps results at 6", () => {
  const suggestions = ["A", "B", "C", "D", "E", "F", "G", "H"];
  const result = getFilteredSuggestions(suggestions, [], "");
  assert.equal(result.length, 6);
});


test("getFilteredSuggestions returns empty array when nothing matches", () => {
  const suggestions = ["Alice", "Bob"];
  const result = getFilteredSuggestions(suggestions, [], "xyz");
  assert.deepEqual(result, []);
});


// ---------------------------------------------------------------------------
// 9. addValue duplicate guard
// ---------------------------------------------------------------------------

test("adding a duplicate value (same case) is silently ignored", () => {
  const state = makeState({ values: ["Alice"], inputValue: "Alice", suggestions: [], highlightedIndex: -1 });
  const next = handleKeyDown(state, "Enter");
  assert.deepEqual(next.values, ["Alice"]); // not added twice
  assert.equal(next.inputValue, "");
});


test("adding a duplicate value (different case) is silently ignored", () => {
  const state = makeState({ values: ["Alice"], inputValue: "alice", suggestions: [], highlightedIndex: -1 });
  const next = handleKeyDown(state, "Enter");
  assert.deepEqual(next.values, ["Alice"]);
});


test("adding a whitespace-only value is silently ignored", () => {
  const state = makeState({ values: [], inputValue: "   ", suggestions: [], highlightedIndex: -1 });
  const next = handleKeyDown(state, "Enter");
  assert.deepEqual(next.values, []);
});


// ---------------------------------------------------------------------------
// 10. Full keyboard workflow — add multiple values, navigate, remove
// ---------------------------------------------------------------------------

test("complete workflow: type, navigate suggestions, select, then remove", () => {
  let state = makeState({ inputValue: "a" }); // matches Alice
  // Arrow down to highlight Alice
  state = handleKeyDown(state, "ArrowDown");
  assert.equal(state.highlightedIndex, 0);
  // Enter confirms Alice
  state = handleKeyDown(state, "Enter");
  assert.ok(state.values.includes("Alice"));
  assert.equal(state.inputValue, "");
  // Backspace removes Alice
  state = handleKeyDown(state, "Backspace");
  assert.deepEqual(state.values, []);
});


test("Tab on first suggestion when none highlighted adds first match", () => {
  const state = makeState({ inputValue: "b", highlightedIndex: -1 });
  const next = handleKeyDown(state, "Tab");
  // 'b' matches 'Bob'
  assert.ok(next.values.includes("Bob"));
});


test("blur commits typed text to values (form-submit regression)", () => {
  const state = makeState({
    inputValue: "ফারসীম মান্নান মহাম্মাদী",
    values: [],
    suggestions: [],
  });
  const after = simulateBlur(state);
  assert.ok(after.values.includes("ফারসীম মান্নান মহাম্মাদী"),
    "Writer name should be in values after blur");
  assert.equal(after.inputValue, "", "inputValue should be cleared after blur");
});


test("blur on empty input does not add an empty tag", () => {
  const state = makeState({ inputValue: "", values: [] });
  const after = simulateBlur(state);
  assert.deepEqual(after.values, []);
});


test("blur on whitespace-only input does not add a tag", () => {
  const state = makeState({ inputValue: "   ", values: [] });
  const after = simulateBlur(state);
  assert.deepEqual(after.values, []);
});


test("blur does not add a duplicate that is already in values", () => {
  const state = makeState({
    inputValue: "Alice",
    values: ["Alice"],
    suggestions: [],
  });
  const after = simulateBlur(state);
  assert.deepEqual(after.values, ["Alice"]); // still only one entry
  assert.equal(after.inputValue, "");
});


// ---------------------------------------------------------------------------
// 12. Arrow-navigation blocked while input has text (expected behaviour)
// ---------------------------------------------------------------------------

test("ArrowRight does NOT navigate when input still has text (user is typing)", () => {
  let rightCalled = false;
  const state = makeState({
    inputValue: "ফারসীম মান্নান মহাম্মাদী",
    suggestions: [],
  });
  handleKeyDown(state, "ArrowRight", { onArrowRight: () => { rightCalled = true; } });
  assert.ok(!rightCalled,
    "onArrowRight must not fire while the writer name is still in the input");
});


test("ArrowRight navigates after blur commits the text (input becomes empty)", () => {
  let rightCalled = false;
  let state = makeState({
    inputValue: "ফারসীম মান্নান মহাম্মাদী",
    values: [],
    suggestions: [],
  });
  // Simulate blur committing the text
  state = simulateBlur(state);
  assert.equal(state.inputValue, "");
  assert.ok(state.values.includes("ফারসীম মান্নান মহাম্মাদী"));
  // Now ArrowRight should navigate
  handleKeyDown(state, "ArrowRight", { onArrowRight: () => { rightCalled = true; } });
  assert.ok(rightCalled,
    "onArrowRight should fire once the input is empty after blur");
});


// ---------------------------------------------------------------------------
// 13. Internal whitespace normalization
// ---------------------------------------------------------------------------

test("internal extra spaces are collapsed when confirming text via Enter", () => {
  const state = makeState({
    inputValue: "ফারসীম  মান্নান  মহাম্মাদী",
    values: [],
    suggestions: [],
  });
  const next = handleKeyDown(state, "Enter");
  assert.ok(next.values.includes("ফারসীম মান্নান মহাম্মাদী"));
  assert.ok(!next.values.includes("ফারসীম  মান্নান  মহাম্মাদী"));
});


test("internal extra spaces are collapsed when committing text via blur", () => {
  const state = makeState({
    inputValue: "ফারসীম  মান্নান  মহাম্মাদী",
    values: [],
    suggestions: [],
  });
  const after = simulateBlur(state);
  assert.ok(after.values.includes("ফারসীম মান্নান মহাম্মাদী"));
  assert.ok(!after.values.includes("ফারসীম  মান্নান  মহাম্মাদী"));
});

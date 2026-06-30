/**
 * Tests for the TagInput component's keyboard interaction logic.
 *
 * The component is a React component and cannot be rendered in the Node
 * test runner without a full DOM/jsdom environment.  We therefore extract
 * and test the *pure state-transition logic* that drives the keyboard
 * behaviour, covering:
 *
 *   1. Arrow-Up / Arrow-Down navigation through the suggestion dropdown
 *   2. Tab   — selects the highlighted suggestion (or first if none)
 *   3. Enter / comma — confirms the highlighted suggestion or free-text
 *   4. Escape — closes the dropdown
 *   5. Backspace — removes the last tag when input is empty
 *   6. ArrowLeft / ArrowRight — field navigation (only when input is empty)
 *   7. Filtering logic — suggestions shown/hidden correctly
 *   8. addValue guard — duplicates are silently skipped
 */

import assert from "node:assert/strict";
import test from "node:test";

// ---------------------------------------------------------------------------
// Pure state machine extracted from TagInput.jsx
// (keeps tests independent of React/DOM)
// ---------------------------------------------------------------------------

function normalizeToken(value) {
  return (value || "").trim().toLowerCase();
}

/**
 * Build the same filteredSuggestions array that TagInput renders.
 */
function getFilteredSuggestions(suggestions, values, inputValue) {
  const normalizedValues = new Set((values || []).map((v) => normalizeToken(v)));
  return suggestions
    .filter((entry) => !normalizedValues.has(normalizeToken(entry)))
    .filter((entry) =>
      inputValue.trim()
        ? entry.toLowerCase().includes(inputValue.trim().toLowerCase())
        : true
    )
    .slice(0, 6);
}

/**
 * Simulate the full TagInput state and its key-down handler.
 *
 * Returns a new state object after processing the key event — never mutates
 * the input state.
 *
 * State shape:
 *   { values, inputValue, highlightedIndex, focused, suggestions }
 *
 * Side-effect callbacks (all optional):
 *   onArrowLeft, onArrowRight
 */
function handleKeyDown(state, key, { onArrowLeft, onArrowRight } = {}) {
  const {
    values = [],
    inputValue = "",
    highlightedIndex = -1,
    suggestions = [],
  } = state;

  const normalizedValues = new Set((values || []).map((v) => normalizeToken(v)));
  const filteredSuggestions = getFilteredSuggestions(suggestions, values, inputValue);
  const showSuggestions = filteredSuggestions.length > 0;

  function addValue(nextValue) {
    const trimmedValue = (nextValue || "").trim();
    if (!trimmedValue) return { values, inputValue, highlightedIndex: -1 };
    const normalized = normalizeToken(trimmedValue);
    if (normalizedValues.has(normalized)) {
      return { values, inputValue: "", highlightedIndex: -1 };
    }
    return { values: [...values, trimmedValue], inputValue: "", highlightedIndex: -1 };
  }

  // --- Suggestion-open shortcuts ---
  if (showSuggestions) {
    if (key === "ArrowDown") {
      const next =
        highlightedIndex < filteredSuggestions.length - 1
          ? highlightedIndex + 1
          : 0;
      return { ...state, highlightedIndex: next };
    }
    if (key === "ArrowUp") {
      const next =
        highlightedIndex > 0
          ? highlightedIndex - 1
          : filteredSuggestions.length - 1;
      return { ...state, highlightedIndex: next };
    }
    if (key === "Tab") {
      const target =
        highlightedIndex >= 0
          ? filteredSuggestions[highlightedIndex]
          : filteredSuggestions[0];
      if (target) {
        return { ...state, ...addValue(target) };
      }
      return state;
    }
  }

  // --- Universal shortcuts ---
  if (key === "Enter" || key === ",") {
    if (highlightedIndex >= 0 && filteredSuggestions[highlightedIndex]) {
      return { ...state, ...addValue(filteredSuggestions[highlightedIndex]) };
    }
    return { ...state, ...addValue(inputValue) };
  }

  if (key === "Escape" && showSuggestions) {
    return { ...state, highlightedIndex: -1, focused: false };
  }

  if (key === "ArrowLeft" && !inputValue) {
    onArrowLeft?.();
    return state;
  }

  if (key === "ArrowRight" && !inputValue) {
    onArrowRight?.();
    return state;
  }

  if (key === "Backspace" && !inputValue && values?.length) {
    return { ...state, values: values.slice(0, -1) };
  }

  return state;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeState(overrides = {}) {
  return {
    values: [],
    inputValue: "",
    highlightedIndex: -1,
    focused: true,
    suggestions: ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace"],
    ...overrides,
  };
}

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

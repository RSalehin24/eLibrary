export function normalizeToken(value) {
  return (value || "").trim().toLowerCase();
}

export function getFilteredSuggestions(suggestions, values, inputValue) {
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

export function handleKeyDown(state, key, { onArrowLeft, onArrowRight } = {}) {
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
    const trimmedValue = (nextValue || "").trim().replace(/\s+/g, " ");
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

export function makeState(overrides = {}) {
  return {
    values: [],
    inputValue: "",
    highlightedIndex: -1,
    focused: true,
    suggestions: ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace"],
    ...overrides,
  };
}

export function simulateBlur(state) {
  // mirrors the fixed onBlur: addValue(inputValue) runs synchronously
  const trimmedValue = (state.inputValue || "").trim().replace(/\s+/g, " ");
  if (!trimmedValue) return state;
  const normalizedValues = new Set((state.values || []).map((v) => normalizeToken(v)));
  const normalized = normalizeToken(trimmedValue);
  if (normalizedValues.has(normalized)) {
    return { ...state, inputValue: "" };
  }
  return { ...state, values: [...(state.values || []), trimmedValue], inputValue: "" };
}

import { useId, useState } from "react";

function normalizeToken(value) {
  return (value || "").trim().toLowerCase();
}

export default function TagInput({ label, values, onChange, suggestions = [], placeholder = "" }) {
  const inputId = useId();
  const [inputValue, setInputValue] = useState("");
  const [focused, setFocused] = useState(false);
  const normalizedValues = new Set((values || []).map((value) => normalizeToken(value)));
  const filteredSuggestions = suggestions
    .filter((entry) => !normalizedValues.has(normalizeToken(entry)))
    .filter((entry) =>
      inputValue.trim() ? entry.toLowerCase().includes(inputValue.trim().toLowerCase()) : true
    )
    .slice(0, 6);

  function addValue(nextValue) {
    const trimmedValue = (nextValue || "").trim();
    if (!trimmedValue) {
      return;
    }

    const normalized = normalizeToken(trimmedValue);
    if (normalizedValues.has(normalized)) {
      setInputValue("");
      return;
    }

    onChange([...(values || []), trimmedValue]);
    setInputValue("");
  }

  function removeValue(targetValue) {
    onChange((values || []).filter((value) => value !== targetValue));
  }

  return (
    <label className="tag-field" htmlFor={inputId}>
      <span className="fact-label">{label}</span>
      <div className={`tag-input-shell${focused ? " is-focused" : ""}`}>
        <div className="tag-chip-list">
          {(values || []).map((value) => (
            <button key={`${label}-${value}`} type="button" className="tag-chip" onClick={() => removeValue(value)}>
              <span>{value}</span>
              <span aria-hidden="true">×</span>
            </button>
          ))}
          <input
            id={inputId}
            type="text"
            value={inputValue}
            placeholder={placeholder}
            onFocus={() => setFocused(true)}
            onBlur={() => {
              addValue(inputValue);
              window.setTimeout(() => setFocused(false), 120);
            }}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === ",") {
                event.preventDefault();
                addValue(inputValue);
                return;
              }

              if (event.key === "Backspace" && !inputValue && values?.length) {
                event.preventDefault();
                removeValue(values[values.length - 1]);
              }
            }}
          />
        </div>
        {focused && filteredSuggestions.length ? (
          <div className="tag-suggestion-list" role="listbox">
            {filteredSuggestions.map((entry) => (
              <button
                key={`${label}-suggestion-${entry}`}
                type="button"
                className="tag-suggestion"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => addValue(entry)}
              >
                {entry}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </label>
  );
}

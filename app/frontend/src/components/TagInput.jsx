import { forwardRef, useId, useImperativeHandle, useRef, useState } from "react";

function normalizeToken(value) {
  return (value || "").trim().toLowerCase();
}

const TagInput = forwardRef(function TagInput(
  { label, values, onChange, suggestions = [], placeholder = "", onArrowLeft, onArrowRight },
  ref
) {
  const inputId = useId();
  const inputRef = useRef(null);
  const [inputValue, setInputValue] = useState("");
  const [focused, setFocused] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const normalizedValues = new Set((values || []).map((value) => normalizeToken(value)));
  const filteredSuggestions = suggestions
    .filter((entry) => !normalizedValues.has(normalizeToken(entry)))
    .filter((entry) =>
      inputValue.trim() ? entry.toLowerCase().includes(inputValue.trim().toLowerCase()) : true
    )
    .slice(0, 6);

  const showSuggestions = focused && filteredSuggestions.length > 0;

  // Expose a focus() method to parent via ref
  useImperativeHandle(ref, () => ({
    focus() {
      inputRef.current?.focus();
    },
  }));

  function addValue(nextValue) {
    const trimmedValue = (nextValue || "").trim();
    if (!trimmedValue) {
      return;
    }

    const normalized = normalizeToken(trimmedValue);
    if (normalizedValues.has(normalized)) {
      setInputValue("");
      setHighlightedIndex(-1);
      return;
    }

    onChange([...(values || []), trimmedValue]);
    setInputValue("");
    setHighlightedIndex(-1);
  }

  function removeValue(targetValue) {
    onChange((values || []).filter((value) => value !== targetValue));
  }

  function handleKeyDown(event) {
    if (showSuggestions) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setHighlightedIndex((prev) =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : 0
        );
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredSuggestions.length - 1
        );
        return;
      }
      if (event.key === "Tab") {
        // Select highlighted suggestion, or the first one if none highlighted
        const target =
          highlightedIndex >= 0
            ? filteredSuggestions[highlightedIndex]
            : filteredSuggestions[0];
        if (target) {
          event.preventDefault();
          addValue(target);
        }
        return;
      }
    }

    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      if (highlightedIndex >= 0 && filteredSuggestions[highlightedIndex]) {
        addValue(filteredSuggestions[highlightedIndex]);
      } else {
        addValue(inputValue);
      }
      return;
    }

    if (event.key === "Escape" && showSuggestions) {
      event.preventDefault();
      setHighlightedIndex(-1);
      setFocused(false);
      inputRef.current?.blur();
      return;
    }

    // Left/Right arrow: move to previous/next field when input is empty
    if (event.key === "ArrowLeft" && !inputValue && onArrowLeft) {
      event.preventDefault();
      onArrowLeft();
      return;
    }

    if (event.key === "ArrowRight" && !inputValue && onArrowRight) {
      event.preventDefault();
      onArrowRight();
      return;
    }

    if (event.key === "Backspace" && !inputValue && values?.length) {
      event.preventDefault();
      removeValue(values[values.length - 1]);
    }
  }

  return (
    <label className="tag-field" htmlFor={inputId}>
      <span className="tag-field-header">
        <span className="fact-label">{label}</span>
        <span className="tag-field-nav">
          {onArrowLeft && (
            <button
              type="button"
              className="tag-field-nav-btn"
              aria-label={`Go to previous field`}
              tabIndex={-1}
              onMouseDown={(e) => e.preventDefault()}
              onClick={onArrowLeft}
            >
              &#8592;
            </button>
          )}
          {onArrowRight && (
            <button
              type="button"
              className="tag-field-nav-btn"
              aria-label={`Go to next field`}
              tabIndex={-1}
              onMouseDown={(e) => e.preventDefault()}
              onClick={onArrowRight}
            >
              &#8594;
            </button>
          )}
        </span>
      </span>
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
            ref={inputRef}
            type="text"
            value={inputValue}
            placeholder={placeholder}
            autoComplete="off"
            onFocus={() => setFocused(true)}
            onBlur={() => {
              // Commit any typed-but-not-yet-confirmed text immediately,
              // so clicking "Add & next" (or any submit) still captures the value.
              addValue(inputValue);
              window.setTimeout(() => {
                setFocused(false);
                setHighlightedIndex(-1);
              }, 120);
            }}
            onChange={(event) => {
              setInputValue(event.target.value);
              setHighlightedIndex(-1);
            }}
            onKeyDown={handleKeyDown}
          />
        </div>
        {showSuggestions ? (
          <div className="tag-suggestion-list" role="listbox">
            {filteredSuggestions.map((entry, index) => (
              <button
                key={`${label}-suggestion-${entry}`}
                type="button"
                className={`tag-suggestion${index === highlightedIndex ? " is-highlighted" : ""}`}
                role="option"
                aria-selected={index === highlightedIndex}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setHighlightedIndex(index)}
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
});

export default TagInput;

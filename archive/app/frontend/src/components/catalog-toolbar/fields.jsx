import { useState, useMemo, useRef, useEffect } from "react";

export function countActiveFilters(filters, fields, defaultFilters) {
  return fields.reduce((count, field) => {
    const currentValue = String(filters[field.key] ?? "").trim();
    const defaultValue = String(defaultFilters[field.key] ?? "").trim();
    return !currentValue || currentValue === defaultValue ? count : count + 1;
  }, 0);
}

function SearchableSelect({ options, value, onChange, placeholder = "Search..." }) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Clear search on open/close
  useEffect(() => {
    if (isOpen) {
      setSearch("");
    }
  }, [isOpen]);

  const selectedOption = useMemo(() => {
    return options.find(opt => String(opt.value) === String(value)) || options[0] || { value: "", label: "Any" };
  }, [options, value]);

  const filteredOptions = useMemo(() => {
    const term = search.toLowerCase().trim();
    if (!term) return options;
    return options.filter(
      (opt) =>
        String(opt.label || "").toLowerCase().includes(term) ||
        String(opt.value || "").toLowerCase().includes(term)
    );
  }, [options, search]);

  return (
    <div className="custom-select-container" ref={containerRef} data-expanded={isOpen ? "true" : "false"}>
      <button
        type="button"
        className="custom-select-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className="custom-select-trigger-label">{selectedOption.label}</span>
        <span className="custom-select-trigger-arrow">▼</span>
      </button>

      {isOpen && (
        <div className="custom-select-dropdown">
          <div className="custom-select-search-wrapper" onClick={(e) => e.stopPropagation()}>
            <input
              type="text"
              className="custom-select-search-input"
              placeholder={placeholder}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
          <ul className="custom-select-options-list">
            {filteredOptions.length === 0 ? (
              <li className="custom-select-no-results">No results found</li>
            ) : (
              filteredOptions.map((option) => (
                <li key={option.value}>
                  <button
                    type="button"
                    className={`custom-select-option-button ${String(option.value) === String(value) ? "is-selected" : ""}`}
                    onClick={() => {
                      onChange({ target: { value: option.value } });
                      setIsOpen(false);
                    }}
                  >
                    {option.label}
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

export function renderField(field, filters, setFilters) {
  const value = filters[field.key] ?? "";
  if (field.type === "searchable-select") {
    return (
      <SearchableSelect
        options={field.options || []}
        value={value}
        onChange={(event) =>
          setFilters({ ...filters, [field.key]: event.target.value })
        }
        placeholder="Search..."
        data-testid={field.testId}
      />
    );
  }
  if (field.type === "select") {
    return (
      <select
        value={value}
        onChange={(event) =>
          setFilters({ ...filters, [field.key]: event.target.value })
        }
        data-testid={field.testId}
      >
        {(field.options || []).map((option) => (
          <option key={`${field.key}-${option.value}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }
  return (
    <input
      type={field.type || "text"}
      value={value}
      placeholder={field.placeholder || ""}
      onChange={(event) => setFilters({ ...filters, [field.key]: event.target.value })}
      data-testid={field.testId}
    />
  );
}


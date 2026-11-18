import { useCallback, useEffect, useState } from "react";

function readBoolean(key, fallback) {
  try {
    const value = window.sessionStorage.getItem(key);
    if (value === null) return fallback;
    return value === "1";
  } catch {
    return fallback;
  }
}

function writeBoolean(key, value) {
  try {
    window.sessionStorage.setItem(key, value ? "1" : "0");
  } catch {
    // ignore
  }
}

// Stores a boolean preference under the given key in sessionStorage. Defaults
// to `initial` when no value has been written yet.
export function useSessionFlag(key, initial = false) {
  const [value, setValue] = useState(() => readBoolean(key, initial));

  useEffect(() => {
    writeBoolean(key, value);
  }, [key, value]);

  const update = useCallback((next) => {
    setValue((current) =>
      typeof next === "function" ? next(current) : Boolean(next),
    );
  }, []);

  return [value, update];
}

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "elibrary:theme";
const VALID = new Set(["light", "dark", "system"]);

function readStoredTheme() {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return VALID.has(value) ? value : "dark";
  } catch {
    return "dark";
  }
}

function applyTheme(theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (theme === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", theme);
  }
}

// Returns [theme, setTheme, resolvedTheme]. `theme` is the user preference
// ("light" | "dark" | "system"). `resolvedTheme` is the concrete value
// currently applied ("light" | "dark").
export function useTheme() {
  const [theme, setThemeState] = useState(readStoredTheme);
  const [systemTheme, setSystemTheme] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    function handleChange(event) {
      setSystemTheme(event.matches ? "dark" : "light");
    }
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  const setTheme = useCallback((next) => {
    if (!VALID.has(next)) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
    setThemeState(next);
  }, []);

  const resolvedTheme = theme === "system" ? systemTheme : theme;
  return [theme, setTheme, resolvedTheme];
}

// Apply the stored theme synchronously before React mounts to avoid a flash
// of the wrong palette. Call once from main.jsx.
export function bootstrapTheme() {
  applyTheme(readStoredTheme());
}

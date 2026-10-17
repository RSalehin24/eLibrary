"use client";
import { useCallback, useEffect, useState } from "react";
import { checkedReaderAppearance, defaultReaderAppearance, type ReaderAppearance } from "./reader-preferences";
const STORAGE_KEY = "library-reader-appearance";
export function useReaderPreferences() {
  const [appearance, setAppearance] = useState(defaultReaderAppearance);
  const [storageError, setStorageError] = useState(false);
  useEffect(() => {
    const timer = requestAnimationFrame(() => { try { const stored = localStorage.getItem(STORAGE_KEY); if (stored) setAppearance(checkedReaderAppearance(JSON.parse(stored))); }
    catch { setStorageError(true); } });
    return () => cancelAnimationFrame(timer);
  }, []);
  const changeAppearance = useCallback((value: ReaderAppearance) => {
    const checked = checkedReaderAppearance(value); setAppearance(checked);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(checked)); setStorageError(false); }
    catch { setStorageError(true); }
  }, []);
  return { appearance, changeAppearance, storageError };
}

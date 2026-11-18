import { useEffect, useRef, useState } from "react";
import { READER_STYLE_URLS, loadReaderRuntime } from "./assets";

// Reader theme indices (matches reader-settings.js THEMES array)
const READER_THEME_LIGHT = 0; // white
const READER_THEME_DARK = 2; // night

const READER_THEME_KEY = "epub_reader_theme_index";

function appendReaderStyles() {
  return READER_STYLE_URLS.map((href) => {
    const node = document.createElement("link");
    node.rel = "stylesheet";
    node.href = href;
    document.head.appendChild(node);
    return node;
  });
}

function destroyReaderInstance(current) {
  current?.instance?.destroy?.();
  current?.styleNodes?.forEach((node) => node.remove());
}

export function useReaderBoot({
  manifestUrl,
  setLoading,
  setError,
  toast,
  resolvedTheme,
}) {
  const [isReaderBooted, setIsReaderBooted] = useState(false);
  const readerRef = useRef(null);

  useEffect(() => {
    if (!manifestUrl) {
      return undefined;
    }

    // Seed the reader's localStorage theme so it boots into the right mode.
    // Only override if no user preference has been explicitly stored for the
    // current session (i.e. the stored value matches a light/dark extreme so
    // we can keep the sync simple).
    try {
      const isDark = resolvedTheme === "dark";
      const targetIndex = isDark ? READER_THEME_DARK : READER_THEME_LIGHT;
      const stored = window.localStorage.getItem(READER_THEME_KEY);
      // Sync when: no stored value, OR stored value is one of our two managed
      // indices (0 or 2) — meaning we were the ones who last set it.
      if (stored === null || stored === "0" || stored === "2") {
        window.localStorage.setItem(READER_THEME_KEY, String(targetIndex));
      }
    } catch {
      // ignore storage errors
    }

    let active = true;
    let instance = null;

    async function mountReader() {
      try {
        const styleNodes = appendReaderStyles();
        const { ensureEpubRuntime, ReaderApplication } =
          await loadReaderRuntime();

        if (!active) {
          styleNodes.forEach((node) => node.remove());
          return;
        }

        await ensureEpubRuntime();
        if (!active) {
          styleNodes.forEach((node) => node.remove());
          return;
        }

        instance = new ReaderApplication();
        instance.init();
        readerRef.current = { styleNodes, instance };
        setIsReaderBooted(true);
      } catch (bootError) {
        const message =
          bootError?.message || "Failed to initialize EPUB reader.";
        setError(message);
        toast.error(message);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    mountReader();
    return () => {
      active = false;
      setIsReaderBooted(false);
      destroyReaderInstance(readerRef.current);
      readerRef.current = null;
    };
  }, [manifestUrl, setError, setLoading, toast]); // eslint-disable-line react-hooks/exhaustive-deps

  // When app theme changes while reader is running, sync reader theme.
  useEffect(() => {
    const instance = readerRef.current?.instance;
    if (!instance || !resolvedTheme) return;
    const targetIndex =
      resolvedTheme === "dark" ? READER_THEME_DARK : READER_THEME_LIGHT;
    instance.applyThemeByIndex?.(targetIndex);
  }, [resolvedTheme]);

  return { isReaderBooted };
}

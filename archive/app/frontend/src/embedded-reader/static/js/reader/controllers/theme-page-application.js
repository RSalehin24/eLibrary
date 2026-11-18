import { queryAll } from "../utils/dom-helpers.js";
import { applyThemeToReaderDocument } from "./theme-document-application.js";

export function applyThemeContainerClass(containerElement, themeIndex) {
  if (!containerElement) return;

  containerElement.classList.add("epub-container");

  Array.from(containerElement.classList).forEach((className) => {
    if (className.startsWith("theme-type-")) {
      containerElement.classList.remove(className);
    }
  });

  containerElement.classList.add(`theme-type-${themeIndex}`);
}

function ensureThemeMeta(head, name, media) {
  const mediaSelector = media ? `[media='${media}']` : ":not([media])";
  let meta = document.querySelector(`meta[name='${name}']${mediaSelector}`);

  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute("name", name);
    if (media) {
      meta.setAttribute("media", media);
    }
    head.appendChild(meta);
  }

  return meta;
}

export function syncSystemThemeColor({
  fallbackColor,
  fallbackThemeColor,
  selectedTheme
}) {
  const color =
    selectedTheme?.style?.body?.background || fallbackColor || fallbackThemeColor;
  const head = document.head || document.querySelector("head");

  if (!head) return;

  ensureThemeMeta(head, "theme-color", "(prefers-color-scheme: light)").setAttribute(
    "content",
    color
  );
  ensureThemeMeta(head, "theme-color", "(prefers-color-scheme: dark)").setAttribute(
    "content",
    color
  );
  ensureThemeMeta(head, "theme-color").setAttribute("content", color);
  ensureThemeMeta(head, "msapplication-navbutton-color").setAttribute("content", color);

  const isAndroid = /android/i.test((navigator.userAgent || "").toLowerCase());
  if (!isAndroid) return;

  if (document.documentElement) {
    document.documentElement.style.backgroundColor = color;
  }
  if (document.body) {
    document.body.style.backgroundColor = color;
  }
}

function collectThemeDocuments({ observedDocuments, rendition }) {
  const docs = [];
  const seenDocs = new Set();
  const addDoc = (doc) => {
    if (!doc || seenDocs.has(doc)) return;
    seenDocs.add(doc);
    docs.push(doc);
  };

  if (rendition?.getContents) {
    rendition.getContents().forEach((content) => {
      const contentDoc = content?.document || content?.window?.document;
      addDoc(contentDoc);
    });
  }

  queryAll("#viewer iframe").forEach((iframe) => {
    addDoc(iframe?.contentDocument || null);
  });

  return { docs, seenDocs };
}

export function applyThemeToCurrentPage({
  clearPendingThemeApplyTimers,
  disconnectThemeObserver,
  observedDocuments,
  rendition,
  scheduleThemeReapply,
  theme,
  themeIndex
}) {
  if (!theme) return;

  const { docs, seenDocs } = collectThemeDocuments({ observedDocuments, rendition });
  Array.from(observedDocuments).forEach((doc) => {
    if (!seenDocs.has(doc)) {
      disconnectThemeObserver(doc);
    }
  });

  clearPendingThemeApplyTimers();

  const applyAllDocs = () => {
    docs.forEach((doc) => {
      applyThemeToReaderDocument({
        disconnectThemeObserver,
        doc,
        observedDocuments,
        theme,
        themeIndex
      });
    });
  };

  applyAllDocs();
  scheduleThemeReapply(applyAllDocs, 60);
  scheduleThemeReapply(applyAllDocs, 220);
  scheduleThemeReapply(applyAllDocs, 600);
}

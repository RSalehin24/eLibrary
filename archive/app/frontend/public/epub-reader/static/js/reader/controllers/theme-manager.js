import {
  DEFAULT_THEME_INDEX,
  DEFAULT_FONT_SIZE,
  MIN_FONT_SIZE,
  MAX_FONT_SIZE,
  FONT_SIZE_STEP,
  APP_THEME_COLOR,
  THEMES,
  STORAGE_KEYS
} from "../reader-settings.js";
import { clamp, queryAll } from "../utils/dom-helpers.js";

export class ReaderThemeManager {
  constructor({
    containerElement,
    themeList = THEMES,
    defaultThemeIndex = DEFAULT_THEME_INDEX,
    defaultFontSize = DEFAULT_FONT_SIZE,
    minFontSize = MIN_FONT_SIZE,
    maxFontSize = MAX_FONT_SIZE,
    fontStep = FONT_SIZE_STEP,
    fallbackThemeColor = APP_THEME_COLOR
  } = {}) {
    this.containerElement = containerElement;
    this.themeList = themeList;
    this.currentThemeIndex = defaultThemeIndex;
    this.currentFontSize = defaultFontSize;
    this.minFontSize = minFontSize;
    this.maxFontSize = maxFontSize;
    this.fontStep = fontStep;
    this.fallbackThemeColor = fallbackThemeColor;
    this.themesApi = null;
    this.observedDocuments = new Set();
    this.pendingThemeApplyTimers = new Set();
  }

  attachThemesApi(themesApi) {
    this.themesApi = themesApi || null;
  }

  getTheme(index) {
    return this.themeList[index];
  }

  getCurrentThemeIndex() {
    return this.currentThemeIndex;
  }

  getCurrentFontSize() {
    return this.currentFontSize;
  }

  setInitialState({ themeIndex, fontSize }) {
    if (Number.isInteger(themeIndex) && this.themeList[themeIndex]) {
      this.currentThemeIndex = themeIndex;
    }

    if (Number.isFinite(fontSize)) {
      this.currentFontSize = clamp(fontSize, this.minFontSize, this.maxFontSize);
    }
  }

  registerThemes() {
    if (!this.themesApi) return;

    this.themeList.forEach((theme) => {
      this.themesApi.register(theme.name, theme.style);
    });
  }

  setFontSize(sizeValue) {
    if (!this.themesApi) return;

    this.themesApi.fontSize(sizeValue);
  }

  changeFontSizeByStep(stepCount) {
    if (!stepCount || !this.themesApi) return false;

    const nextSize = clamp(
      this.currentFontSize + this.fontStep * stepCount,
      this.minFontSize,
      this.maxFontSize
    );

    if (nextSize === this.currentFontSize) return false;

    this.currentFontSize = nextSize;
    this.setFontSize(`${this.currentFontSize}px`);
    this.persistNumber(STORAGE_KEYS.fontSize, this.currentFontSize);
    return true;
  }

  applyThemeByIndex(themeIndex, rendition) {
    if (!this.themesApi || !this.getTheme(themeIndex)) return false;

    return this.setTheme(themeIndex, rendition);
  }

  cycleTheme(rendition) {
    if (!this.themesApi || !this.themeList.length) return false;

    const nextThemeIndex = (this.currentThemeIndex + 1) % this.themeList.length;
    return this.setTheme(nextThemeIndex, rendition);
  }

  setTheme(themeIndex, rendition) {
    const theme = this.getTheme(themeIndex);
    if (!theme || !this.themesApi) return false;

    this.themesApi.select(theme.name);
    this.currentThemeIndex = themeIndex;
    this.persistNumber(STORAGE_KEYS.themeIndex, themeIndex);

    this.applyThemeContainerClass(themeIndex);
    this.applyThemeToCurrentPage(themeIndex, rendition);
    this.syncSystemThemeColor(themeIndex);

    return true;
  }

  persistNumber(key, value) {
    try {
      window.localStorage.setItem(key, String(value));
    } catch {
      // Ignore storage errors and keep runtime behavior intact.
    }
  }

  clearPendingThemeApplyTimers() {
    this.pendingThemeApplyTimers.forEach((timerId) => clearTimeout(timerId));
    this.pendingThemeApplyTimers.clear();
  }

  scheduleThemeReapply(callback, delayMs) {
    const timerId = setTimeout(() => {
      this.pendingThemeApplyTimers.delete(timerId);
      callback();
    }, delayMs);

    this.pendingThemeApplyTimers.add(timerId);
  }

  disconnectThemeObserver(doc) {
    if (!doc) return;

    if (doc.__readerScrollContainer?.classList) {
      doc.__readerScrollContainer.classList.remove("reader-scroll-container");
    }
    doc.__readerScrollContainer = null;
    if (doc.body?.classList) {
      doc.body.classList.remove("reader-scroll-host");
    }

    if (doc.__readerThemeObserver) {
      doc.__readerThemeObserver.disconnect();
      doc.__readerThemeObserver = null;
    }

    if (doc.__readerThemeObserverRaf) {
      cancelAnimationFrame(doc.__readerThemeObserverRaf);
      doc.__readerThemeObserverRaf = null;
    }

    if (doc.__readerThemePendingNodes) {
      doc.__readerThemePendingNodes.clear();
      doc.__readerThemePendingNodes = null;
    }

    this.observedDocuments.delete(doc);
  }

  teardown() {
    this.clearPendingThemeApplyTimers();
    Array.from(this.observedDocuments).forEach((doc) => this.disconnectThemeObserver(doc));
  }

  applyThemeContainerClass(themeIndex) {
    if (!this.containerElement) return;

    this.containerElement.classList.add("epub-container");

    Array.from(this.containerElement.classList).forEach((className) => {
      if (className.startsWith("theme-type-")) {
        this.containerElement.classList.remove(className);
      }
    });

    this.containerElement.classList.add(`theme-type-${themeIndex}`);
  }

  syncSystemThemeColor(themeIndex, fallbackColor = this.fallbackThemeColor) {
    const selectedTheme = this.getTheme(themeIndex);
    const color =
      selectedTheme?.style?.body?.background || fallbackColor || this.fallbackThemeColor;
    const head = document.head || document.querySelector("head");

    if (!head) return;

    const ensureMeta = (name, media) => {
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
    };

    ensureMeta("theme-color", "(prefers-color-scheme: light)").setAttribute(
      "content",
      color
    );
    ensureMeta("theme-color", "(prefers-color-scheme: dark)").setAttribute(
      "content",
      color
    );
    ensureMeta("theme-color").setAttribute("content", color);
    ensureMeta("msapplication-navbutton-color").setAttribute("content", color);

    const isAndroid = /android/i.test((navigator.userAgent || "").toLowerCase());
    if (isAndroid) {
      if (document.documentElement) {
        document.documentElement.style.backgroundColor = color;
      }
      if (document.body) {
        document.body.style.backgroundColor = color;
      }
    }
  }

  applyThemeToCurrentPage(themeIndex, rendition) {
    const theme = this.getTheme(themeIndex);
    if (!theme) return;
    const themeBody = theme.style?.body || {};
    const themeTextColor = themeBody.color || "#000";
    const themeBackground = themeBody.background || "#fff";
    const linkPaletteByTheme = {
      0: {
        default: "#471de4",
        visited: "#471de4",
        hover: "#471de4",
        active: "#471de4"
      },
      1: {
        default: "#1f58b3",
        visited: "#2f74e8",
        hover: "#4a8fff",
        active: "#2f74e8"
      },
      2: {
        default: "#8fcfff",
        visited: "#7bc3ff",
        hover: "#b8e2ff",
        active: "#a1d8ff"
      }
    };
    const scrollbarPaletteByTheme = {
      0: {
        track: "#e8e7e7",
        thumb: "#888",
        thumbHover: "#666"
      },
      1: {
        track: "#efe3c2",
        thumb: "#663403",
        thumbHover: "#582e04"
      },
      2: {
        track: "#242938",
        thumb: "#5a5f73",
        thumbHover: "#6e7489"
      }
    };

    const activeLinkPalette = linkPaletteByTheme[themeIndex] || linkPaletteByTheme[DEFAULT_THEME_INDEX];
    const activeScrollbarPalette =
      scrollbarPaletteByTheme[themeIndex] || scrollbarPaletteByTheme[DEFAULT_THEME_INDEX];
    const iframeLinkDefault = activeLinkPalette.default;
    const iframeLinkVisited = activeLinkPalette.visited;
    const iframeLinkHover = activeLinkPalette.hover;
    const iframeLinkActive = activeLinkPalette.active;
    const scrollbarTrack = activeScrollbarPalette.track;
    const scrollbarThumb = activeScrollbarPalette.thumb;
    const scrollbarThumbHover = activeScrollbarPalette.thumbHover;

    const isDocumentUsable = (doc) => {
      if (!doc || !doc.body || !doc.documentElement) return false;

      const frameElement = doc.defaultView?.frameElement || null;
      if (frameElement && !frameElement.isConnected) return false;
      return true;
    };

    const applyThemeToDocument = (doc) => {
      if (!isDocumentUsable(doc)) return;

      this.disconnectThemeObserver(doc);

      const body = doc.body;
      const getNodeTextLength = (node) => ((node?.textContent || "").trim().length);
      const candidateElements = Array.from(body.children || []).filter((element) => {
        if (!element || element.nodeType !== 1) return false;
        const tagName = (element.tagName || "").toLowerCase();
        return !["script", "style", "link", "meta"].includes(tagName);
      });
      const structuralCandidates = candidateElements.filter((element) => {
        const tagName = (element.tagName || "").toLowerCase();
        return ["div", "main", "section", "article"].includes(tagName);
      });
      const bodyTextLength = getNodeTextLength(body);

      const largestStructuralCandidate = structuralCandidates.reduce((largest, element) => {
        if (!largest) return element;
        return getNodeTextLength(element) > getNodeTextLength(largest) ? element : largest;
      }, null);
      const largestCandidateTextLength = getNodeTextLength(largestStructuralCandidate);
      const largestCandidateCoverage =
        bodyTextLength > 0 ? largestCandidateTextLength / bodyTextLength : 0;
      const bodyCanScroll = body.scrollHeight > body.clientHeight + 1;

      const nextScrollContainer =
        !bodyCanScroll &&
        largestStructuralCandidate &&
        largestCandidateTextLength > 180 &&
        largestCandidateCoverage > 0.5
          ? largestStructuralCandidate
          : null;

      if (
        doc.__readerScrollContainer &&
        doc.__readerScrollContainer !== nextScrollContainer &&
        doc.__readerScrollContainer.classList
      ) {
        doc.__readerScrollContainer.classList.remove("reader-scroll-container");
      }

      if (nextScrollContainer?.classList) {
        nextScrollContainer.classList.add("reader-scroll-container");
        body.classList.add("reader-scroll-host");
        doc.__readerScrollContainer = nextScrollContainer;

        const validateScrollContainer = () => {
          if (!isDocumentUsable(doc)) return;

          const currentContainer = doc.__readerScrollContainer;
          if (!currentContainer || !body?.classList) return;

          const containerCanScroll =
            currentContainer.scrollHeight > currentContainer.clientHeight + 1;
          if (containerCanScroll) return;

          currentContainer.classList.remove("reader-scroll-container");
          body.classList.remove("reader-scroll-host");
          doc.__readerScrollContainer = null;
        };

        requestAnimationFrame(() => {
          validateScrollContainer();
          requestAnimationFrame(validateScrollContainer);
        });
      } else {
        body.classList.remove("reader-scroll-host");
        doc.__readerScrollContainer = null;
      }

      if (doc.head) {
        let mobileReset = doc.getElementById("epub-mobile-reset");
        if (!mobileReset) {
          mobileReset = doc.createElement("style");
          mobileReset.id = "epub-mobile-reset";
          doc.head.appendChild(mobileReset);
        }

        let themeOverrides = doc.getElementById("epub-theme-overrides");
        if (!themeOverrides) {
          themeOverrides = doc.createElement("style");
          themeOverrides.id = "epub-theme-overrides";
          doc.head.appendChild(themeOverrides);
        }

        mobileReset.textContent =
          "@media (max-width: 640px) { html, body { margin: 0 !important; padding: 0 !important; box-sizing: border-box !important; } img, svg, video, canvas { max-width: 100% !important; height: auto !important; } }";

        const forcedThemeTextStyles = `
          body, body * {
            color: ${themeTextColor} !important;
            -webkit-text-fill-color: ${themeTextColor} !important;
          }
          svg text,
          svg tspan {
            fill: ${themeTextColor} !important;
          }
        `;

        themeOverrides.textContent = `
          html {
            -webkit-touch-callout: default;
            -webkit-user-select: text;
            user-select: text;
            box-sizing: border-box !important;
            margin: 0 !important;
            height: 100% !important;
            background: transparent !important;
            background-color: transparent !important;
            scrollbar-gutter: stable;
          }
          body {
            -webkit-touch-callout: default;
            -webkit-user-select: text;
            user-select: text;
            box-sizing: border-box !important;
            margin: 0 !important;
            min-height: 100% !important;
            height: auto !important;
            scrollbar-gutter: stable;
          }
          *, *::before, *::after {
            box-sizing: inherit;
          }
          body {
            color: ${themeTextColor} !important;
            background: ${themeBackground} !important;
            background-color: ${themeBackground} !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-gutter: stable;
          }
          html,
          body,
          .reader-scroll-container {
            scrollbar-color: ${scrollbarThumb} ${scrollbarTrack};
          }
          html::-webkit-scrollbar,
          body::-webkit-scrollbar,
          .reader-scroll-container::-webkit-scrollbar {
            width: 12px;
          }
          html::-webkit-scrollbar-track,
          body::-webkit-scrollbar-track,
          .reader-scroll-container::-webkit-scrollbar-track {
            background: ${scrollbarTrack};
          }
          html::-webkit-scrollbar-thumb,
          body::-webkit-scrollbar-thumb,
          .reader-scroll-container::-webkit-scrollbar-thumb {
            background-color: ${scrollbarThumb};
            border: 3px solid ${scrollbarTrack};
            border-radius: 6px;
          }
          html::-webkit-scrollbar-thumb:hover,
          body::-webkit-scrollbar-thumb:hover,
          .reader-scroll-container::-webkit-scrollbar-thumb:hover {
            background-color: ${scrollbarThumbHover};
          }
          body > div,
          body > main,
          body > section,
          body > article {
            margin: 0 !important;
          }
          body.reader-scroll-host {
            overflow-y: auto !important;
            overflow-x: hidden !important;
          }
          .reader-scroll-container {
            display: block !important;
            min-height: 100% !important;
            max-height: 100% !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-gutter: stable;
            -webkit-overflow-scrolling: touch;
            overscroll-behavior: contain;
          }
          a[href],
          a[href] * {
            color: ${iframeLinkDefault} !important;
            -webkit-text-fill-color: ${iframeLinkDefault} !important;
            text-decoration-color: ${iframeLinkDefault} !important;
          }
          a[href]:visited,
          a[href]:visited * {
            color: ${iframeLinkVisited} !important;
            -webkit-text-fill-color: ${iframeLinkVisited} !important;
            text-decoration-color: ${iframeLinkVisited} !important;
          }
          a[href]:hover,
          a[href]:hover *,
          a[href]:focus,
          a[href]:focus *,
          a[href]:focus-visible,
          a[href]:focus-visible * {
            color: ${iframeLinkHover} !important;
            -webkit-text-fill-color: ${iframeLinkHover} !important;
            text-decoration-color: ${iframeLinkHover} !important;
          }
          a[href]:active,
          a[href]:active * {
            color: ${iframeLinkActive} !important;
            -webkit-text-fill-color: ${iframeLinkActive} !important;
            text-decoration-color: ${iframeLinkActive} !important;
          }
          ${forcedThemeTextStyles}
        `;
      }

      body.style.color = themeTextColor;
      body.style.background = themeBackground;
      body.style.backgroundColor = themeBackground;
      body.style.setProperty("color", themeTextColor, "important");
      body.style.setProperty("background", themeBackground, "important");
      body.style.setProperty("background-color", themeBackground, "important");

      const isSkippableTag = (tagName) => {
        return (
          tagName === "script" ||
          tagName === "style" ||
          tagName === "link" ||
          tagName === "meta" ||
          tagName === "img" ||
          tagName === "video" ||
          tagName === "audio" ||
          tagName === "canvas" ||
          tagName === "source" ||
          tagName === "picture"
        );
      };

      const applyColorToElement = (element) => {
        if (!isDocumentUsable(doc) || !element || element.nodeType !== 1 || !element.isConnected) return;
        if (!element.style) return;

        const tagName = element.tagName ? element.tagName.toLowerCase() : "";
        if (isSkippableTag(tagName)) return;
        if (typeof element.closest === "function" && element.closest("a[href]")) {
          element.style.removeProperty("color");
          element.style.removeProperty("-webkit-text-fill-color");
          if (tagName === "text" || tagName === "tspan") {
            element.style.removeProperty("fill");
          }
          return;
        }

        element.style.setProperty("color", themeTextColor, "important");
        element.style.setProperty("-webkit-text-fill-color", themeTextColor, "important");

        if (tagName === "text" || tagName === "tspan") {
          element.style.setProperty("fill", themeTextColor, "important");
        }
      };

      const shouldRepaintAllElements = doc.__readerAppliedThemeColor !== themeTextColor;
      if (shouldRepaintAllElements) {
        applyColorToElement(body);
        body.querySelectorAll("*").forEach((element) => applyColorToElement(element));
      }

      const flushPendingNodes = () => {
        doc.__readerThemeObserverRaf = null;
        if (!isDocumentUsable(doc)) return;

        const pendingNodes = doc.__readerThemePendingNodes;
        if (!pendingNodes || !pendingNodes.size) return;

        pendingNodes.forEach((node) => {
          if (!node || node.nodeType !== 1 || !node.isConnected) return;

          applyColorToElement(node);
          if (node.querySelectorAll) {
            node.querySelectorAll("*").forEach((child) => applyColorToElement(child));
          }
        });

        pendingNodes.clear();
      };

      const queueNodeForThemeUpdate = (node) => {
        if (!node || node.nodeType !== 1 || !node.isConnected) return;

        if (!doc.__readerThemePendingNodes) {
          doc.__readerThemePendingNodes = new Set();
        }

        doc.__readerThemePendingNodes.add(node);

        if (doc.__readerThemeObserverRaf) return;
        doc.__readerThemeObserverRaf = requestAnimationFrame(flushPendingNodes);
      };

      const observer = new MutationObserver((mutations) => {
        if (!isDocumentUsable(doc)) return;

        mutations.forEach((mutation) => {
          if (mutation.type === "attributes") {
            queueNodeForThemeUpdate(mutation.target);
          }

          if (mutation.type === "childList") {
            mutation.addedNodes.forEach((node) => {
              queueNodeForThemeUpdate(node);
            });
          }
        });
      });

      observer.observe(body, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ["style", "class"]
      });

      doc.__readerThemeObserver = observer;
      doc.__readerAppliedThemeColor = themeTextColor;

      if (doc.documentElement) {
        doc.documentElement.style.background = "transparent";
        doc.documentElement.style.setProperty(
          "background",
          "transparent",
          "important"
        );
        doc.documentElement.style.setProperty(
          "background-color",
          "transparent",
          "important"
        );
      }
      this.observedDocuments.add(doc);
    };

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

    Array.from(this.observedDocuments).forEach((doc) => {
      if (!seenDocs.has(doc)) {
        this.disconnectThemeObserver(doc);
      }
    });

    this.clearPendingThemeApplyTimers();

    const applyAllDocs = () => {
      docs.forEach((doc) => applyThemeToDocument(doc));
    };

    applyAllDocs();
    this.scheduleThemeReapply(applyAllDocs, 60);
    this.scheduleThemeReapply(applyAllDocs, 220);
    this.scheduleThemeReapply(applyAllDocs, 600);
  }
}

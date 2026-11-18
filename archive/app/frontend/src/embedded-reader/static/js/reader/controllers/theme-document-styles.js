const MOBILE_RESET_CSS =
  "@media (max-width: 640px) { html, body { margin: 0 !important; padding: 0 !important; box-sizing: border-box !important; } img, svg, video, canvas { max-width: 100% !important; height: auto !important; } }";

export function ensureThemeStyleElements(doc) {
  if (!doc.head) {
    return null;
  }

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

  return { mobileReset, themeOverrides };
}

export function applyThemeStyleContent({
  doc,
  linkPalette,
  scrollbarPalette,
  themeBackground,
  themeTextColor,
}) {
  const elements = ensureThemeStyleElements(doc);
  if (!elements) return;

  const { mobileReset, themeOverrides } = elements;
  mobileReset.textContent = MOBILE_RESET_CSS;

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
      scrollbar-color: ${scrollbarPalette.thumb} ${scrollbarPalette.track};
    }
    html::-webkit-scrollbar,
    body::-webkit-scrollbar,
    .reader-scroll-container::-webkit-scrollbar {
      width: 12px;
    }
    html::-webkit-scrollbar-track,
    body::-webkit-scrollbar-track,
    .reader-scroll-container::-webkit-scrollbar-track {
      background: ${scrollbarPalette.track};
    }
    html::-webkit-scrollbar-thumb,
    body::-webkit-scrollbar-thumb,
    .reader-scroll-container::-webkit-scrollbar-thumb {
      background-color: ${scrollbarPalette.thumb};
      border: 3px solid ${scrollbarPalette.track};
      border-radius: 6px;
    }
    html::-webkit-scrollbar-thumb:hover,
    body::-webkit-scrollbar-thumb:hover,
    .reader-scroll-container::-webkit-scrollbar-thumb:hover {
      background-color: ${scrollbarPalette.thumbHover};
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
      color: ${linkPalette.default} !important;
      -webkit-text-fill-color: ${linkPalette.default} !important;
      text-decoration-color: ${linkPalette.default} !important;
    }
    a[href]:visited,
    a[href]:visited * {
      color: ${linkPalette.visited} !important;
      -webkit-text-fill-color: ${linkPalette.visited} !important;
      text-decoration-color: ${linkPalette.visited} !important;
    }
    a[href]:hover,
    a[href]:hover *,
    a[href]:focus,
    a[href]:focus *,
    a[href]:focus-visible,
    a[href]:focus-visible * {
      color: ${linkPalette.hover} !important;
      -webkit-text-fill-color: ${linkPalette.hover} !important;
      text-decoration-color: ${linkPalette.hover} !important;
    }
    a[href]:active,
    a[href]:active * {
      color: ${linkPalette.active} !important;
      -webkit-text-fill-color: ${linkPalette.active} !important;
      text-decoration-color: ${linkPalette.active} !important;
    }
    /* Theme-adaptive text selection. The selection background uses the theme's
       link color tinted with the text color for legibility regardless of theme. */
    ::selection {
      background: ${linkPalette.default}55 !important;
      color: ${themeTextColor} !important;
    }
    ::-moz-selection {
      background: ${linkPalette.default}55 !important;
      color: ${themeTextColor} !important;
    }
    ${forcedThemeTextStyles}
  `;
}

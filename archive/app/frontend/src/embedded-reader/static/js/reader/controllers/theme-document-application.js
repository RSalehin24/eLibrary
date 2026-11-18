import { applyThemeStyleContent } from "./theme-document-styles.js";
import {
  createThemeColorApplicator,
  installThemeMutationObserver,
  paintThemeTextColor
} from "./theme-element-coloring.js";
import { resolveThemePalettes } from "./theme-palettes.js";
import { syncReaderScrollContainer } from "./theme-scroll-container.js";

export function isReaderDocumentUsable(doc) {
  if (!doc || !doc.body || !doc.documentElement) return false;

  const frameElement = doc.defaultView?.frameElement || null;
  if (frameElement && !frameElement.isConnected) return false;
  return true;
}

function applyBodyThemeStyles({ body, themeBackground, themeTextColor }) {
  body.style.color = themeTextColor;
  body.style.background = themeBackground;
  body.style.backgroundColor = themeBackground;
  body.style.setProperty("color", themeTextColor, "important");
  body.style.setProperty("background", themeBackground, "important");
  body.style.setProperty("background-color", themeBackground, "important");
}

function applyDocumentElementStyles(doc) {
  if (!doc.documentElement) return;

  doc.documentElement.style.background = "transparent";
  doc.documentElement.style.setProperty("background", "transparent", "important");
  doc.documentElement.style.setProperty(
    "background-color",
    "transparent",
    "important"
  );
}

export function applyThemeToReaderDocument({
  disconnectThemeObserver,
  doc,
  observedDocuments,
  theme,
  themeIndex
}) {
  if (!isReaderDocumentUsable(doc)) return;

  disconnectThemeObserver(doc);

  const body = doc.body;
  const themeBody = theme.style?.body || {};
  const themeTextColor = themeBody.color || "#000";
  const themeBackground = themeBody.background || "#fff";
  const { linkPalette, scrollbarPalette } = resolveThemePalettes(themeIndex);

  syncReaderScrollContainer({
    body,
    doc,
    isDocumentUsable: isReaderDocumentUsable
  });
  applyThemeStyleContent({
    doc,
    linkPalette,
    scrollbarPalette,
    themeBackground,
    themeTextColor
  });
  applyBodyThemeStyles({ body, themeBackground, themeTextColor });

  const applyColorToElement = createThemeColorApplicator({
    doc,
    isDocumentUsable: isReaderDocumentUsable,
    themeTextColor
  });
  paintThemeTextColor({ applyColorToElement, body, doc, themeTextColor });
  installThemeMutationObserver({
    applyColorToElement,
    body,
    doc,
    isDocumentUsable: isReaderDocumentUsable
  });

  doc.__readerAppliedThemeColor = themeTextColor;
  applyDocumentElementStyles(doc);
  observedDocuments.add(doc);
}

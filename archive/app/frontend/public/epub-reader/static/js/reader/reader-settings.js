export const SELECTORS = {
  openEbookPage: ".open-ebook-page",
  epubContents: ".epub-contents",
  readerWrapper: ".reader-wrapper",
  openEpubButton: "#open-epub",
  readerContainer: ".epub-reader-container",
  readerWrapperContainer: ".reader-wrapper-container",
  settingWrapper: ".setting-wrapper",
  epubContainer: ".epub-container",
  viewer: "#viewer"
};

export const THEMES = [
  {
    name: "white",
    style: {
      body: {
        color: "#000",
        background: "#fff"
      }
    }
  },
  {
    name: "sepia",
    style: {
      body: {
        color: "#704214",
        background: "#f4eacd"
      }
    }
  },
  {
    name: "night",
    style: {
      body: {
        color: "#bdcadb",
        background: "#1b1f2a"
      }
    }
  }
];

export const DEFAULT_FONT_SIZE = 20;
export const MIN_FONT_SIZE = 14;
export const MAX_FONT_SIZE = 30;
export const FONT_SIZE_STEP = 2;

export const DEFAULT_THEME_INDEX = 0;
export const APP_THEME_COLOR = "#0B3D2E";

export const VIEWPORT_FALLBACK_CONTENT =
  "width=device-width, initial-scale=1.0, viewport-fit=cover";

export const STORAGE_KEYS = {
  themeIndex: "epub_reader_theme_index",
  fontSize: "epub_reader_font_size"
};

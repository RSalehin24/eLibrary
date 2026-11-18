import { DEFAULT_THEME_INDEX } from "../reader-settings.js";

const LINK_PALETTE_BY_THEME = {
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

const SCROLLBAR_PALETTE_BY_THEME = {
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

export function resolveThemePalettes(themeIndex) {
  return {
    linkPalette:
      LINK_PALETTE_BY_THEME[themeIndex] ||
      LINK_PALETTE_BY_THEME[DEFAULT_THEME_INDEX],
    scrollbarPalette:
      SCROLLBAR_PALETTE_BY_THEME[themeIndex] ||
      SCROLLBAR_PALETTE_BY_THEME[DEFAULT_THEME_INDEX]
  };
}

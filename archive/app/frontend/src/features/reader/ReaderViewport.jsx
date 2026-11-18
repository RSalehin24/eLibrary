import PageLoader from "../../components/PageLoader";

// Matches THEMES array indices in reader-settings.js
const READER_BG_BY_INDEX = { 0: "#fff", 1: "#f4eacd", 2: "#1b1f2a" };
const READER_THEME_KEY = "epub_reader_theme_index";

function getInitialReaderBg(resolvedTheme) {
  try {
    const stored = window.localStorage.getItem(READER_THEME_KEY);
    if (stored !== null) {
      const idx = Number(stored);
      if (READER_BG_BY_INDEX[idx] !== undefined) return READER_BG_BY_INDEX[idx];
    }
  } catch {
    // ignore storage errors
  }
  return resolvedTheme === "dark" ? "#1b1f2a" : "#fff";
}

export default function ReaderViewport({
  isReaderBooted,
  navHidden,
  navigate,
  resolvedTheme,
  targetBookPath,
  toggleAppNav,
}) {
  return (
    <section
      className="reader-page-fullscreen epub-container"
      style={{ backgroundColor: getInitialReaderBg(resolvedTheme) }}
    >
      <section
        className="epub-reader-container"
        id="reader-view"
        aria-label="EPUB reader"
      >
        <div id="epub-contents-panel" className="epub-contents" />
        <div className="reader-wrapper">
          <div id="reader-controls" className="wrapper-nav">
            <div className="icon-wrap-first-two">
              <button
                type="button"
                className="icon-wrap icon-control iconmulu"
                aria-label="Toggle table of contents"
                aria-controls="epub-contents-panel"
                aria-expanded="false"
              >
                <span className="iconfont" aria-hidden="true">
                  <svg viewBox="0 0 24 24" focusable="false">
                    <path d="M4.5 6h0M4.5 12h0M4.5 18h0M9 6h10M9 12h10M9 18h10" />
                  </svg>
                </span>
              </button>
              <div className="icon-anchor">
                <button
                  type="button"
                  className="icon-control iconshezhi"
                  aria-label="Open reading settings"
                  aria-haspopup="true"
                  aria-controls="reader-settings-panel"
                  aria-expanded="false"
                >
                  <span className="iconfont" aria-hidden="true">
                    <svg viewBox="0 0 24 24" focusable="false">
                      <path d="M12 8.75a3.25 3.25 0 1 0 0 6.5a3.25 3.25 0 0 0 0-6.5Z" />
                      <path d="M12 2.75v2.2M12 19.05v2.2M4.95 4.95l1.55 1.55M17.5 17.5l1.55 1.55M2.75 12h2.2M19.05 12h2.2M4.95 19.05l1.55-1.55M17.5 6.5l1.55-1.55" />
                    </svg>
                  </span>
                </button>
                <div
                  id="reader-settings-panel"
                  className="setting-wrapper"
                  role="group"
                  aria-label="Reading settings"
                  aria-hidden="true"
                >
                  <div className="dropdown-caret">
                    <span className="caret-outer" />
                    <span className="caret-inner" />
                  </div>
                  <div className="setting-size">
                    <button
                      type="button"
                      className="size-btn small"
                      data-tag="small"
                      aria-label="Decrease font size"
                    >
                      A
                    </button>
                    <button
                      type="button"
                      className="size-btn big"
                      data-tag="big"
                      aria-label="Increase font size"
                    >
                      A
                    </button>
                  </div>
                  <div className="setting-background">
                    <button
                      type="button"
                      className="bg-btn"
                      data-type="0"
                      aria-pressed="true"
                    >
                      White
                    </button>
                    <button
                      type="button"
                      className="bg-btn"
                      data-type="1"
                      aria-pressed="false"
                    >
                      Sepia
                    </button>
                    <button
                      type="button"
                      className="bg-btn"
                      data-type="2"
                      aria-pressed="false"
                    >
                      Night
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="reader-nav-right">
              <div className="reader-nav-extra">
                <button
                  type="button"
                  id="reader-bookmark-btn"
                  className="icon-wrap icon-control reader-nav-extra-btn"
                  aria-label="Bookmark this page"
                  title="Bookmark this page"
                >
                  <span className="iconfont" aria-hidden="true">
                    <svg
                      viewBox="0 0 24 24"
                      focusable="false"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 3h14a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" />
                    </svg>
                  </span>
                </button>
                <button
                  type="button"
                  className="icon-wrap icon-control reader-nav-extra-btn"
                  onClick={toggleAppNav}
                  aria-label={
                    navHidden ? "Show main header" : "Hide main header"
                  }
                  title={navHidden ? "Show main header" : "Hide main header"}
                >
                  <span className="iconfont" aria-hidden="true">
                    <svg viewBox="0 0 24 24" focusable="false">
                      <rect
                        x="3.25"
                        y="4"
                        width="17.5"
                        height="15.5"
                        rx="2.3"
                        ry="2.3"
                      />
                      <path d="M3.5 9h17" />
                      {navHidden ? (
                        <path d="M12 12.5v4M10.5 15l1.5 1.5 1.5-1.5" />
                      ) : (
                        <path d="M12 16.5v-4M10.5 14l1.5-1.5 1.5 1.5" />
                      )}
                    </svg>
                  </span>
                </button>
                <button
                  type="button"
                  className="icon-wrap icon-control reader-nav-extra-btn"
                  onClick={() => navigate(targetBookPath)}
                  aria-label="Back to book"
                  title="Back to book"
                >
                  <span className="iconfont" aria-hidden="true">
                    <svg viewBox="0 0 24 24" focusable="false">
                      <path d="M9.5 6.5 3.5 12l6 5.5" />
                      <path d="M4 12h16" />
                    </svg>
                  </span>
                </button>
              </div>
            </div>
          </div>
          <div className="reader-chapter-bar" id="reader-chapter-bar">
            <span className="reader-chapter-name" id="reader-chapter-name" />
            <span className="reader-location" id="reader-location" />
          </div>
          <div className="wrapper-main">
            <button
              type="button"
              className="arrow prev-btn"
              aria-label="Previous section"
            >
              <span className="iconfont iconarrow-left" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M14.5 5.5L8 12l6.5 6.5" />
                </svg>
              </span>
            </button>
            <div id="viewer" className="reader-wrapper-container" />
            <button
              type="button"
              className="arrow next-btn"
              aria-label="Next section"
            >
              <span className="iconfont iconarrowright" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M9.5 5.5L16 12l-6.5 6.5" />
                </svg>
              </span>
            </button>
          </div>
        </div>
      </section>

      {!isReaderBooted ? (
        <div className="reader-boot-overlay">
          <PageLoader
            label="Opening reader"
            detail="Loading EPUB reader assets."
            variant="reader"
          />
        </div>
      ) : null}
    </section>
  );
}

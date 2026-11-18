import readerHelpersCssUrl from "../../embedded-reader/static/css/base/helpers.css?url";
import readerIconfontCssUrl from "../../embedded-reader/static/css/base/iconfont.css?url";
import readerResetCssUrl from "../../embedded-reader/static/css/base/reset.css?url";
import readerLayoutCssUrl from "../../embedded-reader/static/css/components/reader-layout.css?url";
import readerShortcutsCssUrl from "../../embedded-reader/static/css/components/shortcuts-dialog.css?url";
import readerThemeOverridesCssUrl from "../../embedded-reader/static/css/themes/theme-overrides.css?url";
import readerThemeTokensCssUrl from "../../embedded-reader/static/css/themes/theme-tokens.css?url";

export const READER_STYLE_URLS = [
  readerResetCssUrl,
  readerIconfontCssUrl,
  readerHelpersCssUrl,
  readerShortcutsCssUrl,
  readerLayoutCssUrl,
  readerThemeTokensCssUrl,
  readerThemeOverridesCssUrl,
];

export async function loadReaderRuntime() {
  const [{ ensureEpubRuntime }, { ReaderApplication }] = await Promise.all([
    import("../../embedded-reader/static/js/vendor/epub-runtime/runtime-entry.js"),
    import("../../embedded-reader/static/js/reader/reader-application.js"),
  ]);

  return { ensureEpubRuntime, ReaderApplication };
}

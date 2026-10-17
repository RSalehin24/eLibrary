import type { ReaderProgress, ReaderSession } from "@/api/types";
import { cfiChapter } from "./reader-cfi-parser";

export type ReadingPosition = { chapter: number; offset: number; fragment?: string; selection?: { start: number; end: number }; legacyCfi?: string; legacyText?: string; restoration?: "missing" };

export function legacyChapter(value: string, chapters: ReaderSession["chapters"]) {
  if (value.startsWith("epubcfi(")) return cfiChapter(value, chapters);
  const path = value.split("#")[0];
  try {
    const decoded = decodeURIComponent(path).replace(/^\.\//, "");
    return chapters.findIndex(chapter => [chapter.path, chapter.href].some(href => href && decodeURIComponent(href).replace(/^\.\//, "") === decoded));
  } catch { return -1; }
}

export function initialPosition(progress: ReaderProgress, chapters: number | ReaderSession["chapters"]): ReadingPosition {
  const chapterCount = typeof chapters === "number" ? chapters : chapters.length;
  const matched = /^chapter:(\d+):(0(?:\.\d+)?|1(?:\.0+)?)$/.exec(progress.last_location);
  const legacy = typeof chapters === "number" ? -1 : legacyChapter(progress.last_location, chapters);
  if (legacy >= 0) return { chapter: legacy, offset: 0, ...(progress.last_location.startsWith("epubcfi(") ? { legacyCfi: progress.last_location } : { fragment: progress.last_location.includes("#") ? `#${progress.last_location.split("#").slice(1).join("#")}` : undefined }) };
  const fraction = Math.min(Math.max(progress.progress_percent / 100 * chapterCount, 0), chapterCount);
  const chapter = matched ? Number(matched[1]) : Math.floor(fraction);
  return { chapter: Math.min(chapter, chapterCount - 1), offset: matched ? Number(matched[2]) : fraction % 1, ...(!matched && progress.last_location ? { restoration: "missing" as const } : {}) };
}

export function positionProgress(position: ReadingPosition, chapterCount: number): ReaderProgress {
  return { last_location: `chapter:${position.chapter}:${position.offset.toFixed(4)}`,
    progress_percent: Math.min(100, (position.chapter + position.offset) / chapterCount * 100) };
}

import type { ReaderProgress } from "@/api/types";

export type ReadingPosition = { chapter: number; offset: number; fragment?: string; selection?: { start: number; end: number } };

export function initialPosition(progress: ReaderProgress, chapterCount: number): ReadingPosition {
  const matched = /^chapter:(\d+):(0(?:\.\d+)?|1(?:\.0+)?)$/.exec(progress.last_location);
  const fraction = Math.min(Math.max(progress.progress_percent / 100 * chapterCount, 0), chapterCount);
  const chapter = matched ? Number(matched[1]) : Math.floor(fraction);
  return { chapter: Math.min(chapter, chapterCount - 1), offset: matched ? Number(matched[2]) : fraction % 1 };
}

export function positionProgress(position: ReadingPosition, chapterCount: number): ReaderProgress {
  return { last_location: `chapter:${position.chapter}:${position.offset.toFixed(4)}`,
    progress_percent: Math.min(100, (position.chapter + position.offset) / chapterCount * 100) };
}

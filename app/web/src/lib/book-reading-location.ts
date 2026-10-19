import type { ReaderProgress, ReaderSession } from "@/api/types";
import { initialPosition } from "./reading-position";

export function bookReadingLocation(progress: ReaderProgress, chapters: ReaderSession["chapters"]) {
  if (!progress.last_location || !chapters.length) return null;
  const position = initialPosition(progress, chapters);
  if (position.restoration === "missing") return null;
  const modern = progress.last_location.startsWith("chapter:");
  if (modern && Number(progress.last_location.split(":")[1]) !== position.chapter) return null;
  const chapter = chapters[position.chapter];
  if (!chapter) return null;
  return { label: chapter.label, number: position.chapter + 1, total: chapters.length, percent: modern ? Math.round(position.offset * 100) : null };
}

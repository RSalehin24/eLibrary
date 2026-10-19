import type { Bookmark, Highlight, ReaderSession } from "@/api/types";
import { initialPosition, legacyChapter, type ReadingPosition } from "./reading-position";

export function annotationPosition(annotation: Bookmark | Highlight, session: ReaderSession): ReadingPosition {
  if ("location" in annotation) return initialPosition({ last_location: annotation.location, progress_percent: 0 }, session.chapters);
  const chapter = legacyChapter(annotation.legacy_cfi || annotation.chapter_href, session.chapters);
  if (chapter < 0) return { chapter: 0, offset: 0, restoration: "missing" };
  return { chapter, offset: 0, selection: annotation.selector ?? undefined, selectionText: annotation.text,
    legacyCfi: annotation.legacy_cfi ?? undefined, legacyText: annotation.text,
    ...(!annotation.selector && !annotation.legacy_cfi ? { restoration: "missing" as const } : {}) };
}

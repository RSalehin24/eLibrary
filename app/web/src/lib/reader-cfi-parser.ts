type Step = { number: number; assertion?: string };
export type CfiPoint = { steps: Step[]; offset: number; assertion?: string; temporal?: number; spatial?: { x: number; y: number } };
export type ParsedCfi = { spineStep: number; spineIndex: number; idref?: string; start: CfiPoint; end?: CfiPoint };

export function splitCfi(value: string, separator: string) {
  const parts: string[] = []; let start = 0, bracket = false, escaped = false;
  for (let index = 0; index < value.length; index++) {
    const character = value[index];
    if (escaped) { escaped = false; continue; }
    if (character === "^") { escaped = true; continue; }
    if (character === "[") { if (bracket) return null; bracket = true; }
    else if (character === "]") { if (!bracket) return null; bracket = false; }
    else if (character === separator && !bracket) { parts.push(value.slice(start, index)); start = index + 1; }
  }
  if (escaped || bracket) return null;
  return [...parts, value.slice(start)];
}

export const unescapeCfi = (value: string) => value.replace(/\^([\s\S])/g, "$1");

export function matchesCfiText(text: string, offset: number, assertion: string) {
  const context = splitCfi(splitCfi(assertion, ";")?.[0] ?? "", ",");
  if (!context || context.length > 2 || offset < 0 || offset > text.length) return false;
  const normalize = (value: string) => value.replace(/\s+/g, " ");
  return normalize(text.slice(0, offset)).endsWith(normalize(unescapeCfi(context[0]))) && (context.length === 1 || normalize(text.slice(offset)).startsWith(normalize(unescapeCfi(context[1]))));
}

function cfiPoint(value: string): CfiPoint | null {
  const steps: Step[] = []; let remaining = value;
  while (remaining.startsWith("/")) {
    const matched = /^\/([1-9]\d*)(?:\[((?:\^.|[^\]^])*)\])?/.exec(remaining);
    if (!matched || steps.length >= 128 || !Number.isSafeInteger(Number(matched[1]))) return null;
    steps.push({ number: Number(matched[1]), assertion: matched[2] }); remaining = remaining.slice(matched[0].length);
  }
  if (/^[~@]/.test(remaining)) {
    const coordinates = cfiCoordinates(remaining);
    return steps.length && steps.at(-1)!.number % 2 === 0 && coordinates ? { steps, offset: 0, ...coordinates } : null;
  }
  const offset = remaining ? /^:(0|[1-9]\d*)(?:\[((?:\^.|[^\]^])*)\])?$/.exec(remaining) : null;
  if (!steps.length || (remaining && !offset) || !Number.isSafeInteger(Number(offset?.[1] ?? 0))) return null;
  return { steps, offset: Number(offset?.[1] ?? 0), assertion: offset?.[2] };
}

function cfiCoordinates(value: string) {
  const number = "(?:0|[1-9]\\d*)(?:\\.\\d+)?";
  const matched = new RegExp(`^(?:~(${number}))?(?:@(${number}):(${number}))?$`).exec(value);
  if (!matched || !matched[1] && !matched[2]) return null;
  const temporal = matched[1] === undefined ? undefined : Number(matched[1]);
  const spatial = matched[2] === undefined ? undefined : { x: Number(matched[2]), y: Number(matched[3]) };
  if (temporal !== undefined && (!Number.isFinite(temporal) || temporal > Number.MAX_SAFE_INTEGER)) return null;
  if (spatial && (spatial.x > 100 || spatial.y > 100)) return null;
  return { ...(temporal === undefined ? {} : { temporal }), ...(spatial ? { spatial } : {}) };
}

export function parseCfi(value: string): ParsedCfi | null {
  if (value.length > 1024 || !value.startsWith("epubcfi(") || !value.endsWith(")")) return null;
  const parts = splitCfi(value.slice(8, -1), "!");
  if (parts?.length !== 2) return null;
  const packagePoint = cfiPoint(parts[0]), local = splitCfi(parts[1], ",");
  if (!packagePoint || packagePoint.offset !== 0 || packagePoint.temporal !== undefined || packagePoint.spatial || packagePoint.steps.length !== 2 || packagePoint.steps.some(step => step.number % 2) || !local || ![1, 3].includes(local.length)) return null;
  const start = cfiPoint(local[0] + (local[1] ?? "")), end = local.length === 3 ? cfiPoint(local[0] + local[2]) : undefined;
  if (!start || end === null) return null;
  const identifier = packagePoint.steps[1].assertion;
  return { spineStep: packagePoint.steps[0].number, spineIndex: packagePoint.steps[1].number / 2 - 1, idref: identifier ? unescapeCfi(splitCfi(identifier, ";")?.[0] ?? "") : undefined, start, end };
}

export function cfiChapter(value: string, chapters: readonly { spine_index?: number; spine_step?: number; idref?: string }[]) {
  const parsed = parseCfi(value);
  if (!parsed) return -1;
  return chapters.findIndex((chapter, index) => (chapter.spine_index ?? index) === parsed.spineIndex && (!chapter.spine_step || chapter.spine_step === parsed.spineStep) && (!parsed.idref || !chapter.idref || chapter.idref === parsed.idref));
}

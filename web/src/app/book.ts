/** Public book metadata (spike stand-in for the generated contract type). */
export interface Book {
  readonly slug: string;
  readonly title: string;
  readonly author: string;
  readonly description: string;
  readonly subjects: readonly string[];
}

function isStringArray(value: unknown): value is readonly string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function hasBookFields(value: unknown): value is Record<keyof Book, unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'slug' in value &&
    'title' in value &&
    'author' in value &&
    'description' in value &&
    'subjects' in value
  );
}

/** Parse at the edge: route data is untyped, so check the shape once before the page uses it. */
export function parseBook(value: unknown): Book {
  if (!hasBookFields(value)) {
    throw new TypeError('book data missing');
  }
  const { slug, title, author, description, subjects } = value;
  if (
    typeof slug !== 'string' ||
    typeof title !== 'string' ||
    typeof author !== 'string' ||
    typeof description !== 'string' ||
    !isStringArray(subjects)
  ) {
    throw new TypeError('book data malformed');
  }
  return { slug, title, author, description, subjects };
}

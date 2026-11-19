/** Public book metadata (spike stand-in for the generated contract type). */
export interface Book {
  readonly slug: string;
  readonly title: string;
  readonly author: string;
  readonly description: string;
  readonly subjects: readonly string[];
}

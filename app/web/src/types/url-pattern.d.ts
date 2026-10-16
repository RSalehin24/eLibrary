import type { URLPattern as FrameworkURLPattern } from "next/dist/compiled/@edge-runtime/primitives/url";

// Next.js uses URLPattern globals that predate TypeScript 5.9's DOM declarations.
// Reuse the framework's shipped types rather than disabling library checking.
declare global {
  type URLPattern = FrameworkURLPattern;
  type URLPatternInput = Exclude<ConstructorParameters<typeof FrameworkURLPattern>[0], undefined>;
  interface URLPatternOptions {
    ignoreCase?: boolean;
  }
}

"use client";

import { translateFieldError } from "@/lib/field-errors";
import { useSiteLanguage } from "./site-language";

export function SiteFieldErrors({ errors }: { errors: string[] }) {
  const { language } = useSiteLanguage();
  return errors.map((message) => translateFieldError(language, message)).join(" ");
}

import type { Metadata } from "next";
import { getAdminLanguage } from "./admin-language-server";
import { translateSite } from "./site-language";
import { siteName } from "./site";

export async function localizeMetadata(metadata: Metadata): Promise<Metadata> {
  const language = await getAdminLanguage();
  const t = (text: string) => translateSite(language, text);
  let title = metadata.title;
  if (typeof title === "string") title = t(title);
  else if (title && "default" in title) title = { ...title, default: t(title.default), template: title.template.replace(siteName, t(siteName)) };
  else if (title && "absolute" in title) title = { ...title, absolute: t(title.absolute) };
  return { ...metadata, title, description: metadata.description ? t(metadata.description) : metadata.description,
    other: { ...metadata.other, "library:ui-title": typeof metadata.title === "string" ? metadata.title : "" } };
}

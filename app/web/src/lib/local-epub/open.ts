import { readLocalArchive } from "./archive";
import { readLocalPackage } from "./package";
import { LocalBookResources } from "./resources";

export async function openLocalBook(file: File) {
  if (!/\.epub$/i.test(file.name) || !file.size || file.size > 24 * 1024 * 1024) throw new Error("invalid_epub");
  const files = await readLocalArchive(file);
  return new LocalBookResources(files, readLocalPackage(files));
}

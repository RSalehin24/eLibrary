import { constants } from "node:fs";
import { copyFile, lstat, mkdir, readFile, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";

const checksum = async (filename) => createHash("sha256").update(await readFile(filename)).digest("hex");

async function copyImmutableFile(source, target) {
  try { await copyFile(source, target, constants.COPYFILE_EXCL); }
  catch (error) {
    if (error.code !== "EEXIST") throw error;
    if (!(await lstat(target)).isFile()) throw new Error("An existing deployment asset is not an ordinary file.");
    if (await checksum(source) !== await checksum(target)) throw new Error("An existing deployment asset has different bytes.");
  }
}

async function publishDirectory(source, target) {
  await mkdir(target, { recursive: true });
  if (!(await lstat(target)).isDirectory()) throw new Error("The deployment destination must be a directory.");
  for (const entry of await readdir(source, { withFileTypes: true })) {
    const input = path.join(source, entry.name), output = path.join(target, entry.name);
    if (entry.isDirectory()) await publishDirectory(input, output);
    else if (entry.isFile()) await copyImmutableFile(input, output);
    else throw new Error("Deployment assets must be ordinary files or directories.");
  }
}

await publishDirectory(process.env.STATIC_SOURCE ?? "/app/.next/static", process.env.STATIC_DESTINATION ?? "/data/next-static");
process.stdout.write("Static assets published; previous deployment files retained.\n");

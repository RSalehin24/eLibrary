import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(new URL("../../../app/web/package.json", import.meta.url));
const ts = require("typescript");
const modules = new Map();

async function moduleURL(path) {
  if (modules.has(path.href)) return modules.get(path.href);
  let source = ts.transpileModule(readFileSync(path, "utf8"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
  for (const match of [...source.matchAll(/from "(\.[^"]+)"/g)]) {
    const dependency = new URL(match[1].endsWith(".ts") ? match[1] : `${match[1]}.ts`, path);
    source = source.replace(match[0], `from "${await moduleURL(dependency)}"`);
  }
  const result = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  modules.set(path.href, result);
  return result;
}

export async function typescriptModule(path) { return import(await moduleURL(path)); }

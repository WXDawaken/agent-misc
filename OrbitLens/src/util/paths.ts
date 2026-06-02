import path from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";

export const packageRoot = findPackageRoot(path.dirname(fileURLToPath(import.meta.url)));

export function resolveFromRoot(...segments: string[]): string {
  return path.resolve(packageRoot, ...segments);
}

function findPackageRoot(start: string): string {
  let current = start;
  for (;;) {
    if (existsSync(path.join(current, "package.json"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      throw new Error(`Could not find package root from ${start}`);
    }
    current = parent;
  }
}

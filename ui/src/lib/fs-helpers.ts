import fs from "fs";
import path from "path";

const ROOT = path.join(process.cwd(), "..");

export function readJsonFile<T>(relativePath: string): T | null {
  try {
    const fullPath = path.join(ROOT, relativePath);
    const raw = fs.readFileSync(fullPath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function readTextFile(relativePath: string): string | null {
  try {
    const fullPath = path.join(ROOT, relativePath);
    return fs.readFileSync(fullPath, "utf-8");
  } catch {
    return null;
  }
}

export function fileExists(relativePath: string): boolean {
  return fs.existsSync(path.join(ROOT, relativePath));
}

export function listJsonFiles(relativePath: string): string[] {
  try {
    const fullPath = path.join(ROOT, relativePath);
    return fs
      .readdirSync(fullPath)
      .filter((f) => f.endsWith(".json"))
      .sort();
  } catch {
    return [];
  }
}

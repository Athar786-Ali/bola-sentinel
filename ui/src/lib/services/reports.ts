import fs from 'fs';
import path from 'path';
import { readTextFile, fileExists } from '../fs-helpers';

const ROOT = path.join(process.cwd(), '..');

export interface ReportFile {
  name: string;
  path: string;
}

export function listReports(): ReportFile[] {
  try {
    const resultsDir = path.join(ROOT, 'results');
    if (!fs.existsSync(resultsDir)) return [];

    return fs.readdirSync(resultsDir)
      .filter(file => file.endsWith('.md'))
      .map(file => ({
        name: file.replace('.md', ''),
        path: `results/${file}`
      }));
  } catch (error) {
    console.error('Error listing reports:', error);
    return [];
  }
}

export function getReport(name: string): string | null {
  const relativePath = `results/${name}.md`;
  if (!fileExists(relativePath)) {
    return null;
  }
  return readTextFile(relativePath);
}

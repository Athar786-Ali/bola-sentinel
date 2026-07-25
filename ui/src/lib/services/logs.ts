import fs from 'fs';
import path from 'path';
import { readTextFile } from '../fs-helpers';

const ROOT = path.join(process.cwd(), '..');

function listLogFiles(subDir: string): string[] {
  try {
    const fullPath = path.join(ROOT, 'logs', subDir);
    if (!fs.existsSync(fullPath)) return [];
    
    return fs.readdirSync(fullPath)
      .filter(file => file.endsWith('.log') || file.endsWith('.json') || file.endsWith('.txt'))
      .sort((a, b) => b.localeCompare(a)); // Newest first by name usually
  } catch {
    return [];
  }
}

export function getEvaluationLogs(): { filename: string, content: string }[] {
  const files = listLogFiles('evaluation_logs');
  return files.map(filename => ({
    filename,
    content: readTextFile(`logs/evaluation_logs/${filename}`) || ''
  }));
}

export function getLLMOutputs(): { filename: string, content: string }[] {
  const files = listLogFiles('llm_outputs');
  return files.map(filename => ({
    filename,
    content: readTextFile(`logs/llm_outputs/${filename}`) || ''
  }));
}

export function getVerificationLogs(): { filename: string, content: string }[] {
  const files = listLogFiles('verification_logs');
  return files.map(filename => ({
    filename,
    content: readTextFile(`logs/verification_logs/${filename}`) || ''
  }));
}

import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const rootDir = path.join(process.cwd(), '..');
    const logsDir = path.join(rootDir, 'logs');
    
    const categories: Record<string, string[]> = {
      evaluation: [],
      llm_outputs: [],
      verification: []
    };

    const getFiles = (subDir: string) => {
      const fullPath = path.join(logsDir, subDir);
      if (fs.existsSync(fullPath)) {
        return fs.readdirSync(fullPath).filter(f => fs.statSync(path.join(fullPath, f)).isFile());
      }
      return [];
    };

    categories.evaluation = getFiles('evaluation_logs');
    categories.llm_outputs = getFiles('llm_outputs');
    categories.verification = getFiles('verification_logs');

    return NextResponse.json({ categories });
  } catch (error) {
    console.error('Error listing logs:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

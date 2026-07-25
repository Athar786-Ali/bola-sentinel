import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ category: string; file: string }> }
) {
  try {
    const { category, file } = await params;
    const validCategories = ['evaluation_logs', 'llm_outputs', 'verification_logs'];

    let cat = category;
    if (cat === 'evaluation') cat = 'evaluation_logs';
    if (cat === 'verification') cat = 'verification_logs';

    if (!validCategories.includes(cat)) {
      return NextResponse.json({ error: 'Invalid category' }, { status: 400 });
    }

    const rootDir = path.join(process.cwd(), '..');
    const safeFile = path.basename(file);
    const filePath = path.join(rootDir, 'logs', cat, safeFile);

    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const content = fs.readFileSync(filePath, 'utf-8');

    if (safeFile.endsWith('.json')) {
      try {
        const data = JSON.parse(content);
        return NextResponse.json({ data });
      } catch {
        // Return as text below
      }
    }

    return NextResponse.json({ content });
  } catch (error) {
    console.error('Error reading log:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

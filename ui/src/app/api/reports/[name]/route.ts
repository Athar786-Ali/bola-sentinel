import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await params;
    const rootDir = path.join(process.cwd(), '..');
    const resultsDir = path.join(rootDir, 'results');

    let filePath = '';
    if (name.endsWith('_EVALUATION_REPORT.md')) {
      const app = name.replace('_EVALUATION_REPORT.md', '');
      filePath = path.join(resultsDir, 'benchmark_runs', app, 'EVALUATION_REPORT.md');
    } else {
      const safeName = path.basename(name);
      filePath = path.join(resultsDir, safeName);
    }

    if (!filePath.startsWith(resultsDir)) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const content = fs.readFileSync(filePath, 'utf-8');
    return NextResponse.json({ content });
  } catch (error) {
    console.error('Error reading report:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

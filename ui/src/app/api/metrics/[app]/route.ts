import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ app: string }> }
) {
  try {
    const { app } = await params;
    const rootDir = path.join(process.cwd(), '..');
    const filePath = path.join(rootDir, 'results', 'benchmark_runs', app, 'evaluation_metrics.json');
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error reading app metrics:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

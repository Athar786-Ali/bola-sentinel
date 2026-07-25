import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const rootDir = path.join(process.cwd(), '..');
    const filePath = path.join(rootDir, 'results', 'benchmark_runs', 'run_manifest.json');
    
    if (!fs.existsSync(filePath)) {
      return NextResponse.json([]); // Return empty array if no history yet
    }

    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const history = Array.isArray(data) ? data : (data.runs || []);
    
    return NextResponse.json(history);
  } catch (error) {
    console.error('Error reading history:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

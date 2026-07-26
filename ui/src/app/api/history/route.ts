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
    
    // Fix timestamp format for JS Date parsing (YYYYMMDDTHHMMSSZ -> YYYY-MM-DDTHH:MM:SSZ)
    for (const run of history) {
      if (run.run_timestamp && run.run_timestamp.length === 16 && !run.run_timestamp.includes('-')) {
        const ts = run.run_timestamp;
        run.run_timestamp = `${ts.substring(0,4)}-${ts.substring(4,6)}-${ts.substring(6,8)}T${ts.substring(9,11)}:${ts.substring(11,13)}:${ts.substring(13,15)}Z`;
      }
    }
    
    return NextResponse.json(history);
  } catch (error) {
    console.error('Error reading history:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const rootDir = path.join(process.cwd(), '..');
    const resultsDir = path.join(rootDir, 'results');
    
    const reports = [];

    if (fs.existsSync(resultsDir)) {
      const files = fs.readdirSync(resultsDir);
      for (const file of files) {
        if (file.endsWith('.md')) {
          reports.push({
            name: file,
            path: `results/${file}`
          });
        }
      }
    }

    const benchmarkRunsDir = path.join(resultsDir, 'benchmark_runs');
    if (fs.existsSync(benchmarkRunsDir)) {
      const apps = fs.readdirSync(benchmarkRunsDir);
      for (const app of apps) {
        const reportPath = path.join(benchmarkRunsDir, app, 'EVALUATION_REPORT.md');
        if (fs.existsSync(reportPath)) {
          reports.push({
            name: `${app}_EVALUATION_REPORT.md`,
            path: `results/benchmark_runs/${app}/EVALUATION_REPORT.md`
          });
        }
      }
    }

    return NextResponse.json({ reports });
  } catch (error) {
    console.error('Error listing reports:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

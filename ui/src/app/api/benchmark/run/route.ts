import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const { apps = [], force = false } = body;
    
    const rootDir = path.join(process.cwd(), '..');
    
    const args = ['run_benchmark.py'];
    if (apps.length > 0) {
      args.push('--apps');
      args.push(apps.join(','));
    }
    if (force) {
      args.push('--force');
    }
    
    const proc = spawn('python3', args, {
      cwd: rootDir,
      detached: true,
      stdio: 'ignore'
    });
    
    proc.unref(); 
    
    return NextResponse.json({ status: 'started', message: 'Benchmark started' });
  } catch (error) {
    console.error('Error starting benchmark:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

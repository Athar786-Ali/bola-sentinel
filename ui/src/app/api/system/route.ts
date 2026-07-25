import { NextRequest, NextResponse } from 'next/server';
import { execSync } from 'child_process';

export async function GET() {
  const result = {
    python: { installed: false, version: '' },
    docker: { installed: false, running: false, version: '' },
    ollama: { installed: false, running: false }
  };

  try {
    const pythonOut = execSync('python3 --version', { stdio: 'pipe' }).toString().trim();
    result.python.installed = true;
    result.python.version = pythonOut;
  } catch (e) {}

  try {
    const dockerOut = execSync('docker --version', { stdio: 'pipe' }).toString().trim();
    result.docker.installed = true;
    result.docker.version = dockerOut;
    
    try {
      execSync('docker ps', { stdio: 'ignore' });
      result.docker.running = true;
    } catch (e) {}
  } catch (e) {}

  try {
    execSync('ollama --version', { stdio: 'pipe' });
    result.ollama.installed = true;
    
    try {
      execSync('ollama list', { stdio: 'ignore' });
      result.ollama.running = true;
    } catch (e) {}
  } catch (e) {}

  return NextResponse.json(result);
}

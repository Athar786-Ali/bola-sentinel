import { execSync } from 'child_process';
import { SystemHealth } from '../types';

export function getSystemStatus(): SystemHealth {
  const status: SystemHealth = {
    python: { installed: false, version: '' },
    docker: { installed: false, running: false },
    ollama: { installed: false, running: false, model: '' }
  };

  // Check Python
  try {
    const pythonVersion = execSync('python3 --version', { encoding: 'utf-8', stdio: 'pipe' }).trim();
    status.python.installed = true;
    status.python.version = pythonVersion.replace('Python ', '');
  } catch {
    try {
      const pythonVersion = execSync('python --version', { encoding: 'utf-8', stdio: 'pipe' }).trim();
      status.python.installed = true;
      status.python.version = pythonVersion.replace('Python ', '');
    } catch {
      // Python not found
    }
  }

  // Check Docker
  try {
    execSync('docker --version', { encoding: 'utf-8', stdio: 'pipe' });
    status.docker.installed = true;
    
    try {
      execSync('docker info', { encoding: 'utf-8', stdio: 'pipe' });
      status.docker.running = true;
    } catch {
      status.docker.running = false;
    }
  } catch {
    // Docker not found
  }

  // Check Ollama
  try {
    execSync('ollama --version', { encoding: 'utf-8', stdio: 'pipe' });
    status.ollama.installed = true;
    
    try {
      const ollamaList = execSync('ollama list', { encoding: 'utf-8', stdio: 'pipe' }).trim();
      status.ollama.running = true;
      
      // Try to parse out models
      const lines = ollamaList.split('\n');
      if (lines.length > 1) {
        const firstModelLine = lines[1];
        const modelName = firstModelLine.split(/\s+/)[0];
        status.ollama.model = modelName;
      }
    } catch {
      status.ollama.running = false;
    }
  } catch {
    // Ollama not found
  }

  return status;
}

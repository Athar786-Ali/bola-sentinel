import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const rootDir = path.join(process.cwd(), '..');
    const filePath = path.join(rootDir, 'datasets', 'app_registry.json');
    
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const registry = Array.isArray(data) ? data : (data.apps || []);
    
    const filtered = registry.filter((entry: any) => entry.application_name !== 'SCHEMA_PLACEHOLDER');
    
    return NextResponse.json(filtered);
  } catch (error) {
    console.error('Error reading datasets:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

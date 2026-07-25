import { readJsonFile } from '../fs-helpers';
import { RunManifestEntry, AppRegistryEntry } from '../types';

export function getRunManifest(): Record<string, RunManifestEntry> | null {
  return readJsonFile<Record<string, RunManifestEntry>>('results/benchmark_runs/run_manifest.json');
}

export function getAppRegistry(): AppRegistryEntry[] {
  const registry = readJsonFile<AppRegistryEntry[]>('datasets/app_registry.json');
  if (!registry) return [];
  
  // Filter out the SCHEMA_PLACEHOLDER
  return registry.filter(app => app.application_name !== 'SCHEMA_PLACEHOLDER');
}

export function getBenchmarkHistory(): RunManifestEntry[] {
  const manifest = getRunManifest();
  if (!manifest) return [];
  
  // Parse into an array sorted by timestamp (newest first)
  return Object.values(manifest).sort((a, b) => {
    return new Date(b.run_timestamp).getTime() - new Date(a.run_timestamp).getTime();
  });
}

import { readJsonFile } from '../fs-helpers';
import { BenchmarkSummary, AppResults, PooledResults } from '../types';

export function getBenchmarkSummary(): BenchmarkSummary | null {
  return readJsonFile<BenchmarkSummary>('results/benchmark_summary.json');
}

export function getAppMetrics(appName: string): AppResults | null {
  const summary = getBenchmarkSummary();
  if (summary && summary.per_application_results[appName]) {
    return summary.per_application_results[appName];
  }
  
  // Fallback: try to read directly from evaluation_metrics.json
  return readJsonFile<AppResults>(`results/benchmark_runs/${appName}/evaluation_metrics.json`);
}

export function getPooledMetrics(): PooledResults | null {
  const summary = getBenchmarkSummary();
  return summary ? summary.pooled_overall_results : null;
}

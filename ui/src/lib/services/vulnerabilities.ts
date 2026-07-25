import { readJsonFile } from '../fs-helpers';
import { 
  StaticAnalysisRoute, 
  LLMClassifiedRoute, 
  VerifiedRoute, 
  GroundTruthEntry, 
  VulnerabilityRow 
} from '../types';

function determineRiskLevel(verdict: string): string {
  switch (verdict.toUpperCase()) {
    case 'VULNERABLE':
    case 'TRUE_POSITIVE':
    case 'FALSE_NEGATIVE':
      return 'HIGH';
    case 'MAYBE':
    case 'NEEDS_REVIEW':
      return 'MEDIUM';
    case 'FALSE_POSITIVE':
    case 'TRUE_NEGATIVE':
    case 'SAFE':
      return 'LOW';
    default:
      return 'SAFE';
  }
}

export function getVulnerabilities(appName: string): VulnerabilityRow[] {
  const staticResults = readJsonFile<StaticAnalysisRoute[]>(`results/benchmark_runs/${appName}/static_analysis_results.json`) || [];
  const llmResults = readJsonFile<LLMClassifiedRoute[]>(`results/benchmark_runs/${appName}/llm_classified_results.json`) || [];
  const finalResults = readJsonFile<VerifiedRoute[]>(`results/benchmark_runs/${appName}/final_verified_results.json`) || [];
  const groundTruth = readJsonFile<GroundTruthEntry[]>(`datasets/ground_truth/${appName}.json`) || [];

  const routeIds = new Set([
    ...staticResults.map(r => r.route_id),
    ...llmResults.map(r => r.route_id),
    ...finalResults.map(r => r.route_id),
    ...groundTruth.map(r => r.route_id)
  ]);

  const rows: VulnerabilityRow[] = [];

  for (const routeId of Array.from(routeIds)) {
    const staticInfo = staticResults.find(r => r.route_id === routeId);
    const llmInfo = llmResults.find(r => r.route_id === routeId);
    const finalInfo = finalResults.find(r => r.route_id === routeId);
    const truthInfo = groundTruth.find(r => r.route_id === routeId);

    const httpMethod = finalInfo?.http_method || staticInfo?.http_method || truthInfo?.http_method || 'UNKNOWN';
    const endpoint = finalInfo?.route_path || staticInfo?.route_path || truthInfo?.endpoint || 'UNKNOWN';

    rows.push({
      route_id: routeId,
      http_method: httpMethod,
      endpoint: endpoint,
      static_flagged: staticInfo ? true : false,
      llm_flagged: llmInfo?.is_vulnerable || false,
      llm_confidence: llmInfo?.confidence || 0,
      llm_explanation: llmInfo?.explanation || '',
      dynamically_verified: finalInfo?.dynamically_verified || false,
      final_verdict: finalInfo?.final_verdict || 'UNKNOWN',
      ground_truth: truthInfo ? truthInfo.actually_vulnerable : null,
      risk_level: determineRiskLevel(finalInfo?.final_verdict || 'UNKNOWN')
    });
  }

  return rows;
}

// Type definitions for BOLA-Sentinel benchmark data

export interface StageMetrics {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  evaluated: number;
  skipped: number;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
  false_negative_rate: number;
  accuracy?: number;
}

export interface AppResults {
  ground_truth_size: number;
  routes_evaluated: number;
  routes_skipped: number;
  coverage: number;
  stage_1_static_only: StageMetrics;
  stage_2_static_plus_llm: StageMetrics;
  stage_3_final_system: StageMetrics;
  fp_reduction_stage1_to_stage2: number;
  fp_reduction_stage2_to_stage3: number;
  fp_reduction_stage1_to_stage3_total: number;
}

export interface PooledResults {
  stage_1_static_only: StageMetrics;
  stage_2_static_plus_llm: StageMetrics;
  stage_3_final_system: StageMetrics;
  fp_reduction_stage1_to_stage2: number;
  fp_reduction_stage2_to_stage3: number;
  fp_reduction_stage1_to_stage3_total: number;
}

export interface BenchmarkSummary {
  run_timestamp: string;
  applications_tested: string[];
  applications_successful: string[];
  applications_failed: string[];
  per_application_results: Record<string, AppResults>;
  pooled_overall_results: PooledResults;
}

export interface AppRegistryEntry {
  application_name: string;
  source_path: string;
  base_url: string;
  test_users_file: string;
  ground_truth_file: string;
  git_commit: string;
  dataset_version: string;
  _comment?: string;
  _notes?: string[];
}

export interface RunManifestEntry {
  application_name: string;
  run_timestamp: string;
  status: "SUCCESS" | "FAILED" | "SKIPPED";
  duration_seconds: number;
  error: string | null;
  phases_completed: string[];
  results_dir: string;
  git_commit: string;
  dataset_version: string;
  llm_model: string;
  python_version: string;
  benchmark_config: {
    dry_run: boolean;
    force: boolean;
  };
}

export interface StaticAnalysisRoute {
  route_id: string;
  http_method: string;
  route_path: string;
  file_path: string;
  line_number: number;
  language: string;
  object_id_params: string[];
  db_operations: string[];
  auth_check_status: string;
  handler_code_raw: string;
}

export interface LLMClassifiedRoute {
  route_id: string;
  is_vulnerable: boolean;
  confidence: number;
  explanation: string;
  vulnerability_type?: string;
  cwe_id?: string;
}

export interface VerifiedRoute {
  route_id: string;
  http_method: string;
  route_path: string;
  static_flagged: boolean;
  llm_flagged: boolean;
  dynamically_verified: boolean;
  final_verdict: string;
  confidence?: number;
  verification_details?: string;
}

export interface GroundTruthEntry {
  route_id: string;
  http_method: string;
  endpoint: string;
  actually_vulnerable: boolean;
  source: string;
  review_notes?: {
    reviewer: string;
    confidence_score: number;
    rationale: string;
  };
}

export interface VulnerabilityRow {
  route_id: string;
  http_method: string;
  endpoint: string;
  static_flagged: boolean;
  llm_flagged: boolean;
  llm_confidence: number;
  llm_explanation: string;
  dynamically_verified: boolean;
  final_verdict: string;
  ground_truth: boolean | null;
  risk_level: string;
}

export interface BenchmarkStatus {
  running: boolean;
  phase: string;
  app: string;
  progress: number;
  logs: string[];
}

export interface SystemHealth {
  python: { installed: boolean; version: string };
  docker: { installed: boolean; running: boolean };
  ollama: { installed: boolean; running: boolean; model: string };
}

# BOLA-Sentinel Benchmark Summary

> Run timestamp: `20260726T195956Z`  
> Applications tested: 2  
> Successful: 2  |  Failed: 0

## Per-Application Results

### vuln-nodejs-app

| Stage | TP | FP | FN | TN | Precision | Recall | F1 | FPR | FNR |
|-------|----|----|----|----|-----------|--------|-----|-----|-----|
| Stage 1 — Static Only | 2 | 4 | 1 | 0 | 0.333 | 0.667 | 0.444 | 100.0% | 33.3% |
| Stage 2 — Static + LLM | 0 | 0 | 3 | 4 | 0.000 | 0.000 | 0.000 | 0.0% | 100.0% |
| Stage 3 — Full Pipeline | 0 | 0 | 3 | 4 | 0.000 | 0.000 | 0.000 | 0.0% | 100.0% |

### juice_shop

| Stage | TP | FP | FN | TN | Precision | Recall | F1 | FPR | FNR |
|-------|----|----|----|----|-----------|--------|-----|-----|-----|
| Stage 1 — Static Only | 6 | 52 | 0 | 0 | 0.103 | 1.000 | 0.188 | 100.0% | 0.0% |
| Stage 2 — Static + LLM | 5 | 8 | 1 | 44 | 0.385 | 0.833 | 0.526 | 15.4% | 16.7% |
| Stage 3 — Full Pipeline | 1 | 1 | 5 | 51 | 0.500 | 0.167 | 0.250 | 1.9% | 83.3% |

## Multi-Dataset Comparison

| Application | Coverage | Precision | Recall | F1 | FPR | Accuracy |
|-------------|----------|-----------|--------|----|-----|----------|
| vuln-nodejs-app | 85.7% | 0.000 | 0.000 | 0.000 | 0.0% | 0.571 |
| juice_shop | 100.0% | 0.500 | 0.167 | 0.250 | 1.9% | 0.897 |

## Pooled Overall Results

> TP/FP/FN/TN are **summed** across all applications before computing
> metrics — not averaged — to avoid statistical distortion from apps
> with different route counts.

| Stage | TP | FP | FN | TN | Precision | Recall | F1 | FPR | FNR |
|-------|----|----|----|----|-----------|--------|-----|-----|-----|
| **Stage 1** — Static Only | 8 | 56 | 1 | 0 | 0.125 | 0.889 | 0.219 | 100.0% | 11.1% |
| **Stage 2** — Static + LLM | 5 | 8 | 4 | 48 | 0.385 | 0.556 | 0.455 | 14.3% | 44.4% |
| **Stage 3** — Full Pipeline | 1 | 1 | 8 | 55 | 0.500 | 0.111 | 0.182 | 1.8% | 88.9% |

## False-Positive Reduction — Primary Research Claim

| Transition | FP Before | FP After | Reduction |
|------------|-----------|----------|-----------|
| Stage 1 → Stage 2 (adding LLM reasoning) | 56 | 8 | **48** fewer FPs |
| Stage 2 → Stage 3 (adding dynamic verification) | 8 | 1 | **7** fewer FPs |
| Stage 1 → Stage 3 **(total)** | 56 | 1 | **55** fewer FPs |

Adding LLM reasoning and then dynamic verification reduced false positives by a total of **55** across the full benchmark (from 56 in static-only to 1 in the full pipeline).

## Reproducibility

Every run is fully logged:
- `results/benchmark_runs/<app>/`  — per-app phase outputs
- `results/benchmark_runs/run_manifest.json`  — run manifest with status + duration
- `logs/evaluation_logs/benchmark_20260726T195956Z.json`  — full aggregated log


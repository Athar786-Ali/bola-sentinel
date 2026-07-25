# Evaluation Migration Report

> This report documents the evaluation correctness fix applied after an
> independent verification audit identified two bugs in the metrics
> computation layer.

---

## 1. Root Cause — Bug 1: Confusion Matrix Iteration

**Location**: `src/bola_sentinel/evaluation/metrics.py` → `compute_confusion_matrix()`

**Root cause**: The function iterated over `routes` (the pipeline output list)
instead of `ground_truth.keys()`. Any ground-truth route that the static
analyzer never discovered was silently excluded from the confusion matrix.

**Impact**: False Negatives were suppressed to 0 whenever the pipeline missed
a vulnerable route entirely. This made Recall appear undefined (0/0 → 0.0)
rather than honestly 0.0 (0/(0+4) → 0.0), and TN was under-counted because
safe routes the pipeline never found were also invisible.

**Fix**: The confusion matrix now iterates over `ground_truth.keys()`.
For every ground-truth route NOT found in the pipeline:
- `actually_vulnerable = True` → **FN** (missed vulnerability)
- `actually_vulnerable = False` → **TN** (correctly absent safe route)

---

## 2. Root Cause — Bug 2: Ground Truth Loader Contamination

**Location**: `src/bola_sentinel/evaluation/ground_truth_loader.py` → `load_all_ground_truth()`

**Root cause**: The function loaded and merged **every** `.json` file in
`datasets/ground_truth/`, including `EXAMPLE.json` (2 synthetic Juice Shop
entries). This inflated `ground_truth_size` from 8 to 10 and contaminated the
confusion matrix with unrelated route IDs.

**Fix**: Replaced with `load_ground_truth_for_app(app_name, dir_path)` which
loads exactly one file: `{dir_path}/{app_name}.json`. The CLI `evaluate`
command now requires `--app-name`.

---

## 3. Files Modified

| File | Change |
|------|--------|
| `src/bola_sentinel/evaluation/metrics.py` | Rewrote `compute_confusion_matrix` to iterate over GT keys; added `compute_coverage`; added `accuracy` |
| `src/bola_sentinel/evaluation/ground_truth_loader.py` | Replaced `load_all_ground_truth` with `load_ground_truth_for_app`; kept deprecated alias |
| `src/bola_sentinel/evaluation/comparator.py` | Added `coverage` to output dict |
| `src/bola_sentinel/evaluation/__init__.py` | Exported `load_ground_truth_for_app` |
| `src/bola_sentinel/evaluation/report_writer.py` | Added Coverage vs Recall section, accuracy column |
| `src/bola_sentinel/cli.py` | Added `--app-name` parameter to `evaluate` command |
| `run_benchmark.py` | Passes `--app-name` to evaluate CLI call |
| `tests/test_evaluation.py` | Rewrote GT loader tests for new API |

## 4. Functions Modified

| Function | Module | Change |
|----------|--------|--------|
| `compute_confusion_matrix()` | `metrics.py` | Iterates over GT keys instead of routes |
| `compute_metrics_from_confusion()` | `metrics.py` | Added `accuracy` metric |
| `compute_coverage()` | `metrics.py` | **New function** |
| `load_ground_truth_for_app()` | `ground_truth_loader.py` | **New function** (replaces `load_all_ground_truth`) |
| `run_progressive_comparison()` | `comparator.py` | Includes `coverage` in output |
| `evaluate()` | `cli.py` | Requires `--app-name`, uses new loader |
| `write_markdown_report()` | `report_writer.py` | Displays Coverage, Accuracy, Coverage vs Recall |

---

## 5. Old Metrics vs New Metrics

### vuln-nodejs-app Benchmark

| Metric | Stage | Before (Buggy) | After (Corrected) | Change Explanation |
|--------|-------|-----------------|--------------------|-------------------|
| **ground_truth_size** | — | 10 | **8** | EXAMPLE.json (2 entries) no longer contaminating |
| **TP** | All | 0 | 0 | No change — pipeline never classified anything as vulnerable |
| **FP** | S1 | 4 | 4 | No change — same 4 non-BOLA routes flagged by static analysis |
| **FP** | S2, S3 | 0 | 0 | No change — LLM correctly filtered them out |
| **FN** | S1 | 0 | **4** | The 4 actual BOLA routes missed by the static analyzer are now correctly counted as False Negatives |
| **FN** | S2, S3 | 0 | **4** | Same — these routes were never discovered by the pipeline |
| **TN** | S1 | 0 | 0 | No change — all 4 discovered safe routes were flagged as positive in S1 |
| **TN** | S2, S3 | 4 | 4 | No change — LLM correctly identified 4 safe routes |
| **Precision** | All | 0.0 | 0.0 | No change — TP = 0 in all stages |
| **Recall** | All | 0.0 | 0.0 | Denominator changed: was 0/(0+0)=0.0, now 0/(0+4)=0.0. Same number, different (honest) reason |
| **F1** | All | 0.0 | 0.0 | No change |
| **FPR** | S1 | 100% | 100% | Denominator changed: was 4/(4+0), now 4/(4+0). Same result |
| **FPR** | S2, S3 | 0% | 0% | No change |
| **Accuracy** | S1 | — | **0.000** | New metric: (0+0)/8 = 0.0 |
| **Accuracy** | S2, S3 | — | **0.500** | New metric: (0+4)/8 = 0.5 |
| **Coverage** | — | — | **50.0%** | New metric: 4 of 8 GT routes discovered |

---

## 6. Explanation of Each Changed Metric

### FN increased from 0 → 4 (all stages)
The 4 actual BOLA vulnerabilities (`GET /notes/user/:userid`, `POST /organization/add-user`, `POST /graphql`, `POST /mongodb-notes/show-notes`) exist in the ground truth but were never surfaced by the static analyzer. Previously, they were invisible to the evaluator. They are now correctly counted as False Negatives.

### ground_truth_size decreased from 10 → 8
`EXAMPLE.json` contained 2 synthetic Juice Shop entries that were being merged into the vuln-nodejs-app evaluation. Removing this contamination gives the correct count of 8 entries specific to vuln-nodejs-app.

### Recall remains 0.0 but with honest semantics
Before: 0/(0+0) = 0/0 → 0.0 by division-safe fallback.
After: 0/(0+4) = 0.0 by actual computation. The pipeline discovered zero true positives out of 4 actual vulnerabilities.

### Coverage = 50.0% (new metric)
4 of 8 ground-truth routes were discovered by the pipeline. This separates "discovery capability" from "classification accuracy."

### Accuracy = 0.5 at Stage 2 and 3 (new metric)
(TP + TN) / total = (0 + 4) / 8 = 0.5. The pipeline correctly classifies half the ground-truth entries (the 4 safe routes it discovered), but misses the other half entirely.

---

## 7. Remaining Limitations

1. **Static analyzer scope**: The analyzer only extracts `router.post(...)` patterns with explicit middleware. It misses `GET` routes with path parameters, `router.route().post()` chains, and `router.use()` mounts. This is the primary driver of the 50% coverage gap and will be addressed in future work.

2. **Recall cannot improve without static analyzer expansion**: Since all 4 actual BOLA routes use patterns the static analyzer does not recognize, Recall will remain 0.0 on this benchmark until the analyzer is extended or a complementary discovery mechanism is added.

3. **Single benchmark application**: The corrected metrics are based on one application. Additional benchmark targets (Juice Shop, Strapi) are needed for statistical confidence.

4. **The FP reduction claim remains valid**: The LLM stage correctly eliminated 4/4 false positives (100% FP reduction). This claim is unaffected by the evaluation bug fix because it depends only on the routes the pipeline actually processed.

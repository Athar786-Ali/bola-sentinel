# Benchmark Guide

> How to add new applications, CVE findings, and run reproducible
> benchmark evaluations with BOLA-Sentinel.

---

## Overview

The benchmark system sits entirely on top of the existing pipeline
(Phases 1-4). It adds **no new detection logic**. Its sole job is:

1. Manage ground-truth datasets for multiple target applications.
2. Orchestrate the 4-phase pipeline per application via subprocess calls.
3. Aggregate results into pooled precision/recall/F1/FPR/FNR across the
   entire benchmark.

```
datasets/
  app_registry.json          ← master list of all target applications
  ground_truth/
    juice_shop.json           ← ground truth for OWASP Juice Shop
    <cve_app_name>.json       ← ground truth per CVE-affected app
  juice_shop/
    (cloned repo + test_users.json)
  real_cves/
    <cve_app_name>/
      (cloned repo + test_users.json)
  dataset_schema.py           ← DatasetEntry pydantic model
  collect_dataset.py          ← CLI for adding new entries
  validate_dataset.py         ← pre-benchmark validation

run_benchmark.py              ← orchestrator (project root)
results/benchmark_runs/       ← per-app pipeline output artifacts
results/benchmark_summary.json
results/benchmark_summary.md
```

---

## 1. Adding a New Vulnerable Application

### Step 1 — Clone the target repository

```bash
# For CVE-affected applications:
git clone https://github.com/<org>/<repo> datasets/real_cves/<cve_app_name>/

# For Juice Shop:
git clone https://github.com/juice-shop/juice-shop datasets/juice_shop/
```

### Step 2 — Create its test_users.json

Create `datasets/real_cves/<cve_app_name>/test_users.json` with the Phase 3
attacker/victim schema:

```json
{
  "user_a": {
    "auth_header": "Bearer <attacker_token>",
    "user_id": "1",
    "owned_object_ids": {
      "orders": ["10"],
      "projects": ["20"]
    }
  },
  "user_b": {
    "auth_header": "Bearer <victim_token>",
    "user_id": "2",
    "owned_object_ids": {
      "orders": ["12"],
      "projects": ["21"]
    }
  }
}
```

Keys in `owned_object_ids` must match resource path segments in the
target API (e.g., `"orders"` matches `/orders/{orderId}/cancel`).

### Step 3 — Register in app_registry.json

Add an entry to `datasets/app_registry.json`:

```json
{
  "application_name": "<cve_app_name>",
  "source_path": "datasets/real_cves/<cve_app_name>/",
  "base_url": "http://localhost:<port>",
  "test_users_file": "datasets/real_cves/<cve_app_name>/test_users.json",
  "ground_truth_file": "datasets/ground_truth/<cve_app_name>.json"
}
```

### Step 4 — Discover route_ids from the analyzer

Run the static analyzer to find the exact route_id format for each route
you want to label:

```bash
bola-sentinel analyze datasets/real_cves/<cve_app_name>/
# Opens: results/static_analysis_results.json
```

Find the route you want and copy its exact `"route_id"` value (e.g.,
`"DELETE_/api/Orders/1_88"`). **Do not guess or reconstruct this value.**
The analyzer is the authoritative source.

### Step 5 — Add ground-truth entries

```bash
python datasets/collect_dataset.py add \
  --app         <cve_app_name> \
  --vuln-name   "Order deletion BOLA via DELETE /api/Orders/:id" \
  --route-id    "DELETE_/api/Orders/1_88" \   # ← EXACT value from Step 4
  --method      DELETE \
  --route       "/api/Orders/:id" \
  --vulnerable-version "2.3.0" \
  --patched-version    "2.4.0" \
  --expected-verdict   true \
  --source      cve \
  --cve-id      "CVE-2024-12345" \
  --notes       "No ownership check; any user can delete any order"
```

Repeat for each route you want to benchmark (both vulnerable and
safe/true-negative routes).

### Step 6 — Validate

```bash
python datasets/validate_dataset.py
# Must print: RESULT: PASSED
```

Fix any errors before proceeding. Common mistakes:
- Wrong route_id (doesn't match analyzer output → silent join failure)
- Duplicate route_id in the same file
- Missing app_registry entry

### Step 7 — Run the benchmark

```bash
python run_benchmark.py --apps <cve_app_name>
```

---

## 2. Adding a New CVE Finding to an Existing Application

If you have a new CVE for an already-registered application:

```bash
# Step 1: Find route_id from analyzer output.
bola-sentinel analyze datasets/real_cves/<app_name>/
# → check results/static_analysis_results.json

# Step 2: Add entry.
python datasets/collect_dataset.py add \
  --app         <app_name> \
  --vuln-name   "..." \
  --route-id    "<exact_id_from_analyzer>" \
  ...

# Step 3: Validate.
python datasets/validate_dataset.py

# Step 4: Re-run benchmark for this app only.
python run_benchmark.py --apps <app_name> --force
```

---

## 3. Defining expected_verdict Correctly

> **Rule: `expected_verdict` must NEVER be set from the tool's own output.**

`expected_verdict` represents ground truth — what the route's access control
behaviour actually is, independently of what BOLA-Sentinel finds.

| Source | Acceptable? |
|--------|-------------|
| CVE report explicitly identifies the vulnerable route | ✅ Yes |
| Patch commit removes/adds an authorization check | ✅ Yes |
| Official security advisory from the vendor | ✅ Yes |
| Manual code review tracing the full call path | ✅ Yes |
| "The tool flagged it, so it must be vulnerable" | ❌ No — this is circular |
| "The tool didn't flag it, so it must be safe" | ❌ No — FN contamination |

Setting expected_verdict from tool output makes every metric trivially
perfect and destroys the scientific validity of the benchmark.

---

## 4. Benchmark Resumption

If a benchmark run is interrupted (e.g., application #3 crashes):

```bash
# Re-run — apps with existing results/benchmark_runs/<app>/ are skipped.
python run_benchmark.py

# Force re-run of specific apps only:
python run_benchmark.py --apps <app_name> --force

# Force re-run of ALL apps:
python run_benchmark.py --force
```

Per-app results are written to `results/benchmark_runs/<app>/` after
each successful run. The manifest is written after every app so a crash
mid-benchmark never loses previous results.

---

## 5. Understanding the run_manifest.json

`results/benchmark_runs/run_manifest.json` is updated after every app
and records:

```json
[
  {
    "application_name": "juice_shop",
    "run_timestamp": "20240101T120000Z",
    "status": "SUCCESS",
    "duration_seconds": 42.3,
    "error": null,
    "phases_completed": ["analyze", "classify", "verify", "evaluate"],
    "results_dir": "results/benchmark_runs/juice_shop"
  }
]
```

`status` is one of: `SUCCESS` | `FAILED` | `SKIPPED`

---

## 6. Understanding Pooled vs Per-App Metrics

The benchmark computes two kinds of results:

**Per-application**: independent confusion matrix per app, from
`results/benchmark_runs/<app>/evaluation_metrics.json`.

**Pooled overall**: TP/FP/FN/TN are **summed** across all apps, then
precision/recall/F1/FPR/FNR are computed once from the combined counts.

> ⚠ Averaging percentages (e.g. mean FPR across apps) is statistically
> misleading when apps have very different route counts. Pooling raw
> counts avoids this distortion.

---

## 7. Full Command Reference

```bash
# Add a new ground-truth entry
python datasets/collect_dataset.py add [options]

# Validate all ground-truth files
python datasets/validate_dataset.py

# Run the full benchmark
python run_benchmark.py

# Run specific apps only
python run_benchmark.py --apps juice_shop cve_2024_xyz

# Re-run everything (disable resumption)
python run_benchmark.py --force

# Preview subprocess commands without executing
python run_benchmark.py --dry-run
```

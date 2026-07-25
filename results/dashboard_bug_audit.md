# Dashboard Bug Audit Report

**Date:** 2026-07-26  
**Author:** Automated audit via verify_dashboard_consistency.py  

---

## Bug 1 — "LLM Flagged: 0" with impossible "Confirmed BOLA" counts

### Root Cause
The API route `ui/src/app/api/vulnerabilities/[app]/route.ts` (line 64) read 
`llm.is_vulnerable` — a top-level field that doesn't exist in the pipeline 
schema. The real field is **`llm.llm_classification.is_vulnerable`** (nested 
object per `ClassifiedRoute` in `schemas.py`). Since `is_vulnerable` was 
always `undefined`, every route evaluated to `false`, producing LLM Flagged = 0.

Additionally, the explorer page's "Confirmed BOLA" stat was computing 
`data.filter(d => d.ground_truth === true).length` — counting ground truth 
labels, NOT dynamically confirmed vulnerabilities. This created the illusion 
of confirmed BOLAs existing when dynamic verification hadn't confirmed any.

The same bug affected `llm_confidence` (reading `llm.confidence` instead of 
`llm.llm_classification.confidence`) and the verification status (reading 
`v.dynamically_verified` instead of `v.verification.verification_status`).

### What Was Fixed
- `vulnerabilities/[app]/route.ts`: Changed `llm.is_vulnerable` → `llm.llm_classification?.is_vulnerable`
- Same for confidence and explanation fields
- Verification mapping: `v.verification.verification_status === 'CONFIRMED_VULNERABLE'`
- Explorer page: Split into 4 separate stats (Analyzed Routes, LLM Flagged, Dynamically Confirmed, Ground Truth Vulnerable)

### Before/After

| Metric | App | Before (wrong) | After (correct) |
|---|---|---|---|
| LLM Flagged | juice_shop | 0 | **9** |
| LLM Flagged | vuln-nodejs-app | 0 | **0** (correct — LLM classified all 4 as not vulnerable) |
| "Confirmed BOLA" label | both | Showed GT count as "confirmed" | **Separated** into GT Vulnerable vs Dynamically Confirmed |
| Dynamically Confirmed | juice_shop | N/A (not shown) | **0** (all INCONCLUSIVE) |
| Dynamically Confirmed | vuln-nodejs-app | N/A | **0** |

---

## Bug 2 — Ground truth "UNKNOWN" entries

### Root Cause
For vuln-nodejs-app, the static analyzer only discovered 4 out of 8 ground 
truth routes. The 4 missing routes (`GET_/notes/user/:userid_57`, 
`POST_/organization/add-user_80`, `POST_/graphql_124`, 
`POST_/mongodb-notes/show-notes_121`) are the actually-vulnerable ones. 
These appeared in the vulnerability table with `http_method: 'UNKNOWN'` 
because the API merge logic created rows from ground truth entries that had 
no corresponding static analysis result.

This is a legitimate **coverage limitation** (coverage = 50%), not a route_id 
formatting mismatch — the static analyzer genuinely didn't find those routes 
in the codebase scan.

For juice_shop, all 58 route_ids match exactly across all pipeline stages — 
no UNKNOWN entries.

### What Was Fixed
- API route now sets `is_matched: boolean` on each row
- Explorer page filters out unmatched entries from the main table
- Unmatched GT entries are displayed as a **warning banner** with the specific 
  route_ids listed, rather than as fake table rows

### Before/After

| Metric | App | Before | After |
|---|---|---|---|
| UNKNOWN method rows | vuln-nodejs-app | 4 rows with checkmarks | **0** (shown as warning banner instead) |
| Unmatched GT warning | vuln-nodejs-app | Not shown | **"4 unmatched ground truth entries"** with IDs |
| UNKNOWN method rows | juice_shop | 0 | 0 (no change needed) |

---

## Bug 3 — Fake datasets (vAmPI, crAPI)

### Root Cause
Five pages used **hardcoded mock data** instead of fetching from API endpoints:

1. **`datasets/page.tsx`** (line 28): `setTimeout` returning `[{app_name: 'vAmPI', ...}, {app_name: 'crAPI', ...}]` — never called `/api/datasets`
2. **`history/page.tsx`** (line 29): Hardcoded array with vAmPI/crAPI run entries
3. **`results/page.tsx`** (line 53): Fetched `/api/metrics` but never used the response — all charts used hardcoded `stageData`, `radarData`, `fpReductionData`
4. **`logs/page.tsx`** (line 8): Used `MOCK_LOGS` array
5. **`reports/page.tsx`** (line 9): Used `MOCK_REPORTS` and `MOCK_MD`

### What Was Fixed
All 5 pages completely rewritten to fetch from their real API endpoints:
- Datasets: `/api/datasets` + `/api/metrics` for ground truth sizes and coverage
- History: `/api/history` for real run entries
- Results: `/api/metrics` data used in all Recharts visualizations
- Logs: `/api/logs` + `/api/logs/{category}/{file}` 
- Reports: `/api/reports` + `/api/reports/{name}`

### Before/After

| Page | Before | After |
|---|---|---|
| Datasets | vAmPI (GT: 42, 85%), crAPI (GT: 156, 92%) | **vuln-nodejs-app** (GT: 8, 50%), **juice_shop** (GT: 58, 100%) |
| History | 3 mock entries with vAmPI/crAPI | Real run history from `run_manifest.json` |
| Results charts | Static hardcoded numbers | Real TP/FP/FN/TN from `benchmark_summary.json` |
| Logs | 4 mock log lines | Real log files from `logs/` directories |
| Reports | Mock markdown text | Real `.md` reports from `results/` |

---

## Bug 4 — Verification

### Script Created
`scripts/verify_dashboard_consistency.py` — independently recomputes metrics 
from raw pipeline JSON files and compares against the dashboard API output.

### Verification Results

```
============================================================
  Verifying: juice_shop
============================================================
  [COMPARISON]
    LLM Flagged                     File=   9  API=   9  ✅ PASS
    Dynamically Confirmed           File=   0  API=   0  ✅ PASS
    Ground Truth Vulnerable         File=   6  API=   6  ✅ PASS
    Ground Truth Size               File=  58  API=  58  ✅ PASS
    Unmatched GT Entries            File=   0  API=   0  ✅ PASS

============================================================
  Verifying: vuln-nodejs-app
============================================================
  [COMPARISON]
    LLM Flagged                     File=   0  API=   0  ✅ PASS
    Dynamically Confirmed           File=   0  API=   0  ✅ PASS
    Ground Truth Vulnerable         File=   4  API=   4  ✅ PASS
    Ground Truth Size               File=   8  API=   8  ✅ PASS
    Unmatched GT Entries            File=   4  API=   4  ✅ PASS

============================================================
  OVERALL: ✅ ALL CHECKS PASSED
============================================================
```

---

## Summary of Current Metrics (Correct)

| Metric | juice_shop | vuln-nodejs-app |
|---|---|---|
| Static routes analyzed | 58 | 4 |
| LLM flagged | 9 | 0 |
| Dynamically confirmed | 0 | 0 |
| Ground truth size | 58 | 8 |
| Ground truth vulnerable | 6 | 4 |
| Coverage | 100% | 50% |
| Stage 2 Precision | 0.222 | 0.0 |
| Stage 2 Recall | 0.333 | 0.0 |
| Stage 2 F1 | 0.267 | 0.0 |
| Stage 3 Precision | 0.0 | 0.0 |
| Stage 3 Recall | 0.0 | 0.0 |
| Stage 3 F1 | 0.0 | 0.0 |

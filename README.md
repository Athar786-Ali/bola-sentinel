# bola-sentinel

> **Research-grade hybrid engine for detecting Broken Object-Level Authorization
> (BOLA) / IDOR vulnerabilities in REST APIs.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-143%20passed-brightgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Research Claim

> *Combining static AST analysis, local-LLM reasoning, and live HTTP
> dynamic verification progressively reduces false positives at each stage
> compared to static analysis alone when detecting BOLA/IDOR vulnerabilities.*

The engine proves this claim by computing precision, recall, F1, and FPR across
three progressive pipeline stages and showing explicit false-positive reduction
numbers for each added stage.

**Priority order (governs every design decision):**

1. **Accuracy** — findings must be correct
2. **False-positive reduction** — each added stage must improve on the previous
3. **Reproducibility** — every prompt, response, and HTTP probe is logged to disk
4. **Explainability** — each finding carries an LLM chain-of-thought
5. **Evaluation metrics** — rigorous comparison against curated ground truth

UI, dashboards, SaaS features, and feature count are explicitly out of scope.

---

## Scope Restrictions

| ✅ In scope | ❌ Out of scope |
|---|---|
| BOLA / IDOR / broken object ownership | SQL injection |
| Object-level authorization model classification | XSS / CSRF / SSRF |
| Dynamic false-positive reduction via live HTTP probes | JWT / secrets / auth-flow flaws |
| Reproducible evaluation against ground-truth datasets | UI or dashboard |
| Local LLM reasoning via Ollama | Paid LLM APIs (OpenAI, Anthropic, …) |

---

## Architecture

```
Target Codebase
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 1 · Static Analysis  (tree-sitter, Python + JavaScript)      │
│  · Identify state-changing routes (POST/PUT/PATCH/DELETE)           │
│  · Extract path parameters and DB operations                        │
│  · Classify auth_check_status: PRESENT | ABSENT | UNCERTAIN         │
│  → results/static_analysis_results.json                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  ABSENT or UNCERTAIN routes only
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 2 · LLM Reasoning  (Ollama · qwen2.5:7b-instruct)           │
│  · Classify authorization model: OWNERSHIP | MEMBERSHIP | …        │
│  · Binary is_vulnerable judgment with confidence                    │
│  · All prompts + responses logged to logs/llm_inputs/outputs/       │
│  → results/llm_classified_results.json                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  is_vulnerable = True routes only
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 3 · Dynamic Verification  (httpx · attacker/victim accounts) │
│  · Build attack probe: user_a token → user_b owned object           │
│  · Capture object state before + after (best-effort)                │
│  · Multi-signal verdict: status code + body + state diff            │
│  · All probes logged to logs/verification_logs/                     │
│  → results/final_verified_results.json                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 4 · Evaluation  (ground truth · progressive comparison)      │
│  · Stage 1: static only · Stage 2: +LLM · Stage 3: +verification   │
│  · Precision / Recall / F1 / FPR / FNR per stage                   │
│  · Explicit FP reduction deltas between stages                      │
│  · Evaluation run logged to logs/evaluation_logs/                   │
│  → results/evaluation_metrics.json + results/EVALUATION_REPORT.md  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
bola-sentinel/
  src/bola_sentinel/
    config.py                      # pydantic-settings configuration
    cli.py                         # Typer CLI (analyze / classify / verify / evaluate)
    models/schemas.py              # FIXED shared Pydantic data contracts
    static_analysis/
      parser_registry.py           # tree-sitter multi-language parser factory
      route_extractor.py           # AST visitor: routes, params, db ops, auth heuristic
      analyzer.py                  # Directory walk orchestrator
    llm_reasoning/
      ollama_client.py             # httpx wrapper for Ollama /api/generate
      prompts.py                   # Structured prompt builders
      logger.py                    # Mandatory LLM I/O logging
      classifier.py                # Orchestrator: filter → prompt → parse → fallback
    dynamic_verification/
      test_user_loader.py          # Load + validate test_users.json
      attack_builder.py            # Build probe URL from route + victim object ID
      state_checker.py             # Before/after object state capture (GET)
      evidence_logger.py           # Write complete JSON evidence per probe
      executor.py                  # Multi-signal verdict logic
      verifier.py                  # Top-level orchestrator
    evaluation/
      ground_truth_loader.py       # Merge all datasets/ground_truth/*.json
      stage_classifiers.py         # Three verdict functions (one per stage)
      metrics.py                   # Confusion matrix + precision/recall/F1/FPR/FNR
      comparator.py                # Progressive three-stage comparison + FP deltas
      standardized_output.py       # Build StandardizedFinding list
      evaluation_logger.py         # Persist evaluation run context for reproducibility
      report_writer.py             # Generate results/EVALUATION_REPORT.md

  datasets/
    ground_truth/                  # One JSON file per dataset (see format below)
      EXAMPLE.json                 # Template to copy

  logs/                            # All audit logs (git-ignored, preserved on disk)
    llm_inputs/                    # Every prompt sent to Ollama
    llm_outputs/                   # Every raw Ollama response
    verification_logs/             # Full HTTP evidence per verification attempt
    evaluation_logs/               # Evaluation run metadata + full metrics

  results/                         # Output JSON and Markdown reports
  tests/                           # 143-test pytest suite (all offline, no network)
  test_users.json                  # Attacker / victim credentials (fill manually)
  .env.example                     # Configuration template
  pyproject.toml
  requirements.txt
```

---

## Quick Start

### 1. Prerequisites

- Python ≥ 3.12
- [Ollama](https://ollama.ai) running locally:
  ```bash
  ollama serve                    # start Ollama if not running
  ollama pull qwen2.5:7b-instruct # pull the reasoning model
  ```

### 2. Install

```bash
git clone <repo>
cd bola-sentinel
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env only if Ollama is on a non-default host/port
```

---

## Running the Full Pipeline

Each phase produces a JSON file consumed by the next phase.

### Phase 1 — Static Analysis

```bash
bola-sentinel analyze /path/to/target/api
# Output: results/static_analysis_results.json
```

### Phase 2 — LLM Classification

```bash
bola-sentinel classify
# Reads:  results/static_analysis_results.json
# Output: results/llm_classified_results.json
# Logs:   logs/llm_inputs/ and logs/llm_outputs/
```

### Phase 3 — Dynamic Verification

Fill in `test_users.json` first (see below), then:

```bash
bola-sentinel verify --target-url http://localhost:3000
# Reads:  results/llm_classified_results.json
# Output: results/final_verified_results.json
# Logs:   logs/verification_logs/
```

### Phase 4 — Evaluation

Add ground-truth files to `datasets/ground_truth/` (see format below), then:

```bash
bola-sentinel evaluate
# Reads:  results/final_verified_results.json + datasets/ground_truth/*.json
# Output: results/evaluation_metrics.json
#         results/EVALUATION_REPORT.md
# Logs:   logs/evaluation_logs/
```

---

## test_users.json Format

Fill in credentials for the **target application** before running Phase 3.
Never commit real tokens to git.

```json
{
  "user_a": {
    "auth_header": "Bearer <attacker_token>",
    "user_id": "1",
    "owned_object_ids": {
      "orders": ["10", "11"],
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

- **user_a** = attacker — their `auth_header` is used in every probe request.
- **user_b** = victim — their `owned_object_ids` supply the target object IDs.
- Keys in `owned_object_ids` must match resource path segments in the target API
  (e.g. `"orders"` matches `/orders/{orderId}/cancel`).

---

## Ground-Truth Format

One JSON file per dataset in `datasets/ground_truth/`:

```json
[
  {
    "route_id": "POST_/api/Products/<id>_88",
    "actually_vulnerable": true,
    "source": "juice_shop",
    "cve_id": null,
    "notes": "Confirmed via manual code review: no ownership check"
  },
  {
    "route_id": "DELETE_/api/Users/<id>_102",
    "actually_vulnerable": false,
    "source": "juice_shop",
    "cve_id": null,
    "notes": "Server verifies session ownership before deletion"
  }
]
```

- `route_id` must exactly match the value in `final_verified_results.json`
- `source`: `"juice_shop"` | `"cve"` | `"advisory"` | `"manual_review"`
- Multiple files are merged automatically; conflicts are logged as warnings

---

## Verdict Decision Logic (Phase 3)

The system **never relies on HTTP status codes alone**:

| HTTP Status | `states_differ()` | Verdict |
|---|---|---|
| 401 / 403 | any | `NOT_VULNERABLE` |
| 404 | any | `NOT_VULNERABLE` |
| 200/201/204 | **True** (object mutated) | `CONFIRMED_VULNERABLE` ★ strong |
| 200/201/204 | **None** (no baseline) + no denial language | `CONFIRMED_VULNERABLE` ★ weak |
| 200/201/204 | **False** (no-op) | `NOT_VULNERABLE` |
| 200/201/204 | None + denial body | `NOT_VULNERABLE` |
| other | any | `INCONCLUSIVE` |

Weak evidence is explicitly flagged in `notes` and `object_state_changed=None`.

---

## Three-Stage Progressive Evaluation (Phase 4)

The evaluation computes metrics at each pipeline checkpoint:

| Stage | What it measures |
|---|---|
| **Stage 1 — Static Only** | `auth_check_status == "ABSENT"` |
| **Stage 2 — Static + LLM** | `llm_classification.is_vulnerable == True` |
| **Stage 3 — Full Pipeline** | `verification_status == "CONFIRMED_VULNERABLE"` |

The report explicitly shows:
- False-positive reduction Stage 1 → 2 (adding LLM reasoning)
- False-positive reduction Stage 2 → 3 (adding dynamic verification)
- Total reduction Stage 1 → 3

---

## Reproducibility

Every run is fully auditable without re-execution:

```
logs/llm_inputs/<timestamp>.txt         # exact prompt sent to Ollama
logs/llm_outputs/<timestamp>.txt        # raw model response + parse status
logs/verification_logs/<route>_<ts>.json  # full HTTP evidence record
logs/evaluation_logs/evaluation_<ts>.json # input counts, GT match counts, metrics
```

Authorization headers are redacted from verification logs before writing.

---

## Testing

```bash
pytest tests/ -v
# 143 tests — all offline (no network, no Ollama required)
```

Test coverage:
- `tests/test_static_analysis.py` — AST parsing, auth heuristics (Flask + Express)
- `tests/test_llm_reasoning.py` — Ollama client, mandatory logging, fallback logic
- `tests/test_dynamic_verification.py` — verdict matrix, evidence logging, state checks
- `tests/test_evaluation.py` — confusion matrices, FP deltas, standardized findings

---

## Related Work (Reference Context)

| Tool | Reported Metric | Source |
|---|---|---|
| BolaRay | 21.86% FPR on their dataset | Published paper |
| IRIS | 84.82% FDR on their dataset | Published paper |

These numbers come from different datasets and experimental setups and **cannot be
directly compared** without running all tools on the same held-out benchmark.

---

## Tech Stack

| Package | Purpose |
|---|---|
| `tree-sitter` + `tree-sitter-python`, `tree-sitter-javascript` | Multi-language AST parsing |
| `pydantic` + `pydantic-settings` | Data validation + typed configuration |
| `httpx` | HTTP probing for dynamic verification |
| `typer` | CLI |
| `pytest` + `pytest-httpx` | Testing (all offline) |
| Ollama (`qwen2.5:7b-instruct`) | Local LLM reasoning — no paid API |

---

## Contributing

This is a research project. Before adding anything, ask:

> *"Does this improve evaluation quality or reproducibility?"*

If not, it is out of scope.

---

## License

MIT

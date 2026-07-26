# Architecture — bola-sentinel

## Project Goal

**bola-sentinel** is a research-grade, hybrid detection engine for
**Broken Object-Level Authorization (BOLA)** and **IDOR** vulnerabilities
in REST APIs.

The **core claim** under investigation is:

> *Combining static analysis (tree-sitter AST parsing) with local-LLM
> reasoning (Ollama) and dynamic HTTP verification produces meaningfully
> fewer false positives than any single technique alone.*

The engine is intentionally narrow in scope (BOLA / IDOR only) so that
evaluation metrics are rigorous and reproducible.

---

## Scope Restrictions

| In scope | Out of scope |
|---|---|
| BOLA / IDOR / broken object ownership | SQL injection |
| Object-level authorization model classification | XSS / CSRF / SSRF |
| Dynamic false-positive reduction via live HTTP probes | JWT / secrets / auth-flow flaws |
| Reproducible evaluation against ground-truth datasets | Any UI, dashboard, or SaaS feature |
| Local LLM reasoning (Ollama only) | Paid LLM APIs (OpenAI, Anthropic, …) |

**Priority order (hardcoded into every design decision):**

1. Accuracy
2. False-positive reduction
3. Reproducibility
4. Explainability
5. Evaluation metrics

UI, dashboard, and feature count are explicitly deprioritised.

---

## Known Limitations

The following API patterns are currently structurally out of scope for the static analyzer and dynamic verification engine:

- **GraphQL APIs**: Single-endpoint APIs (e.g. `POST /graphql`) do not use REST-style path parameters for object IDs and lack HTTP method semantics. The AST extraction and resource-keyword matching logic cannot process them.
- **Complex Router Chaining**: While basic chained routes (`router.route('/path').get(...)`) are supported, heavily nested or dynamically constructed routers may escape static detection.

These limitations are documented and accepted; routes falling into these patterns should be excluded from ground-truth datasets to avoid artificial coverage gaps.

---

## Four-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Target Codebase                          │
│          (Python / JavaScript REST API source files)            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ source files
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 · Static Analysis  (src/bola_sentinel/static_analysis) │
│                                                                 │
│  • tree-sitter + tree-sitter-languages (multi-language AST)     │
│  • Extracts: route paths, HTTP methods, object-id params,       │
│    DB operations, auth-check presence/absence                   │
│  • Output: list[StaticAnalysisResult]                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ StaticAnalysisResult
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2 · LLM Reasoning  (src/bola_sentinel/llm_reasoning)     │
│                                                                 │
│  • Ollama HTTP API (local, no paid keys)                        │
│  • Classifies authorization model: OWNERSHIP / MEMBERSHIP /     │
│    HIERARCHICAL / STATUS / NONE                                  │
│  • Decides is_vulnerable + confidence + suggested probe         │
│  • Every prompt → logs/llm_inputs/<timestamp>.txt               │
│  • Every raw response → logs/llm_outputs/<timestamp>.txt        │
│  • Output: list[ClassifiedRoute]                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ ClassifiedRoute
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3 · Dynamic Verification                                 │
│            (src/bola_sentinel/dynamic_verification)             │
│                                                                 │
│  • httpx for async HTTP probes                                  │
│  • Reads attacker / victim credentials from test_users.json     │
│  • Crafts BOLA probe: attacker token + victim object ID         │
│  • Captures HTTP status, response body excerpt, state change    │
│  • Logs → logs/verification_logs/<timestamp>.json               │
│  • Output: list[VerifiedRoute]                                  │
│                                                                 │
│  ★ This layer is the primary false-positive reduction step.     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ VerifiedRoute
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4 · Evaluation  (src/bola_sentinel/evaluation)           │
│                                                                 │
│  • Compares VerifiedRoute findings against                      │
│    datasets/ground_truth/<dataset>.json                         │
│  • Metrics: precision, recall, F1, false-positive rate          │
│  • Logs → logs/evaluation_logs/<timestamp>.json                 │
│  • Final report → results/<run_id>.json (StandardizedFinding[]) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Choices and Reasoning

| Technology | Role | Rationale |
|---|---|---|
| **Python 3.12+** | Primary language | Match-statement ergonomics, typed dict improvements, `tomllib` stdlib support |
| **tree-sitter + tree-sitter-languages** | Multi-language AST parsing | Language-agnostic grammar queries; supports Python, JS, Go, Java from a single API; no Node.js required |
| **Pydantic v2** | Data contracts | Fast validation, typed JSON serialisation, strict mode for schema enforcement |
| **pydantic-settings** | Configuration management | `.env` + environment variable overlay, zero boilerplate |
| **Ollama (local)** | LLM reasoning | No paid API; reproducible runs with pinned model tags; full prompt/response logging for auditability |
| **httpx** | Dynamic HTTP probes | Async-first, connection pooling, easy cookie/header control |
| **Typer** | CLI | Thin wrapper around Click; auto-generates `--help`; integrates cleanly with Pydantic models |
| **FastAPI** | (Future) API server | Reserved for Phase 4 if a machine-readable API endpoint is needed; not used in core engine |
| **pytest** | Testing | Standard; `pytest-asyncio` for async probe tests; `pytest-httpx` for mocking |

### Why NOT …

- **OpenAI / Anthropic API** — eliminates reproducibility (API behaviour changes without notice), adds cost, and leaks sensitive code snippets off-premises.
- **Node.js / Babel** — tree-sitter-languages provides JavaScript grammar in pure Python; no JS toolchain needed.
- **UI / Dashboard** — scope creep that reduces time available for evaluation quality.

---

## Data Flow and Logging

```
logs/
  llm_inputs/           ← every prompt, timestamped
  llm_outputs/          ← every raw LLM response, timestamped
  verification_logs/    ← HTTP evidence per probe, timestamped
  evaluation_logs/      ← evaluation run output, timestamped
results/                ← final StandardizedFinding[] JSON, one file per run
```

All logs are plain text or JSON — no binary formats — so they can be
committed to a research repository and inspected offline.

#!/usr/bin/env python3
"""
run_benchmark.py — Reproducible multi-application benchmark orchestrator.

This script is an ORCHESTRATION LAYER ONLY.  It calls the existing
`bola-sentinel` CLI commands as subprocesses.  It does NOT reimplement
any pipeline logic from Phases 1-4.

Design principles
-----------------
• No pipeline code lives here — only subprocess calls + result aggregation.
• Resumption: if an app's results already exist, skip it unless --force is set.
• Isolation: each app writes to results/benchmark_runs/{app_name}/ so runs
  never overwrite each other.
• Fault-tolerance: a failure in one app is logged and the benchmark continues
  with the remaining apps.
• Pooled metrics: TP/FP/FN/TN are summed across all apps before computing
  precision/recall/F1/FPR/FNR — averaging percentages across apps with
  different route counts is statistically misleading.

Usage
-----
  python run_benchmark.py              # run all registered apps
  python run_benchmark.py --apps juice_shop cve_2024_xyz
  python run_benchmark.py --force      # re-run even if results exist
  python run_benchmark.py --dry-run    # print commands without executing
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
_REGISTRY_FILE = _PROJECT_ROOT / "datasets" / "app_registry.json"
_BENCHMARK_RUNS_DIR = _PROJECT_ROOT / "results" / "benchmark_runs"
_RESULTS_DIR = _PROJECT_ROOT / "results"
_MANIFEST_FILE = _BENCHMARK_RUNS_DIR / "run_manifest.json"
_LOG_DIR = _PROJECT_ROOT / "logs" / "evaluation_logs"

# Sentinel app names that are placeholders, not real apps.
_PLACEHOLDER_APP_NAMES = frozenset({"SCHEMA_PLACEHOLDER"})


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── Manifest management ────────────────────────────────────────────────────

def _load_manifest() -> list[dict]:
    _BENCHMARK_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if _MANIFEST_FILE.exists():
        try:
            return json.loads(_MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_manifest(entries: list[dict]) -> None:
    _BENCHMARK_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    _MANIFEST_FILE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _upsert_manifest(manifest: list[dict], entry: dict) -> list[dict]:
    """Replace an existing entry by app_name + run_timestamp, or append."""
    updated = [
        m for m in manifest
        if not (m.get("application_name") == entry["application_name"]
                and m.get("run_timestamp") == entry["run_timestamp"])
    ]
    updated.append(entry)
    return updated


# ── Registry ───────────────────────────────────────────────────────────────

def _load_registry() -> list[dict]:
    if not _REGISTRY_FILE.exists():
        raise FileNotFoundError(
            f"app_registry.json not found at {_REGISTRY_FILE}.\n"
            "Run from the project root."
        )
    raw = json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))
    return [
        e for e in raw
        if isinstance(e, dict)
        and e.get("application_name") not in _PLACEHOLDER_APP_NAMES
        and "_comment" not in e
    ]


# ── Subprocess helpers ─────────────────────────────────────────────────────

def _run_cmd(
    args: list[str],
    dry_run: bool = False,
    capture: bool = True,
) -> tuple[int, str]:
    """
    Run a command as a subprocess.

    Returns (returncode, combined stdout+stderr).
    On dry_run, prints the command and returns (0, "").
    """
    cmd_str = " ".join(str(a) for a in args)
    if dry_run:
        print(f"  [DRY-RUN] {cmd_str}")
        return 0, ""

    result = subprocess.run(
        args,
        cwd=str(_PROJECT_ROOT),
        capture_output=capture,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output


# ── Metrics helpers ────────────────────────────────────────────────────────

def _compute_metrics(cm: dict) -> dict:
    """Division-safe precision/recall/F1/FPR/FNR from raw TP/FP/FN/TN."""
    tp, fp, fn, tn = cm["tp"], cm["fp"], cm["fn"], cm["tn"]
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    return {
        **cm,
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
    }


def _pool_confusion_matrices(
    per_app_metrics: list[dict],
    stage_key: str,
) -> dict:
    """Sum TP/FP/FN/TN across all apps for one stage, then compute metrics."""
    pooled = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "evaluated": 0, "skipped": 0}
    for m in per_app_metrics:
        stage = m.get(stage_key, {})
        for k in ("tp", "fp", "fn", "tn", "evaluated", "skipped"):
            pooled[k] += stage.get(k, 0)
    return _compute_metrics(pooled)


# ── Per-application runner ─────────────────────────────────────────────────

def run_benchmark_for_app(
    app_entry: dict,
    run_timestamp: str,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """
    Run the full 4-phase pipeline for a single application.

    Pipeline
    --------
    1. analyze  → run_dir/static_analysis_results.json
    2. classify → run_dir/llm_classified_results.json
    3. verify   → run_dir/final_verified_results.json
                  (uses app's own test_users.json via --test-users)
    4. evaluate → run_dir/evaluation_metrics.json + EVALUATION_REPORT.md
                  (uses the full datasets/ground_truth/ dir; Phase 4 naturally
                   filters to only matching route_ids from final_verified_results)

    Resumption
    ----------
    If run_dir/evaluation_metrics.json already exists and --force is not set,
    the run is skipped and previous results are loaded.

    Returns
    -------
    dict with application_name, status, metrics, error, duration.
    """
    app_name = app_entry["application_name"]
    source_path = str(_PROJECT_ROOT / app_entry["source_path"])
    base_url = app_entry["base_url"]
    test_users_file = str(_PROJECT_ROOT / app_entry["test_users_file"])
    run_dir = _BENCHMARK_RUNS_DIR / app_name
    run_dir.mkdir(parents=True, exist_ok=True)

    static_out  = str(run_dir / "static_analysis_results.json")
    llm_out     = str(run_dir / "llm_classified_results.json")
    verify_out  = str(run_dir / "final_verified_results.json")
    metrics_out = str(run_dir / "evaluation_metrics.json")
    report_out  = str(run_dir / "EVALUATION_REPORT.md")

    # ── Resumption check ──────────────────────────────────────────────
    if not force and (run_dir / "evaluation_metrics.json").exists():
        print(f"\n  [{app_name}] Results exist — skipping (use --force to re-run).")
        metrics = json.loads((run_dir / "evaluation_metrics.json").read_text())
        return {
            "application_name": app_name,
            "run_timestamp": run_timestamp,
            "status": "SKIPPED",
            "duration_seconds": 0,
            "error": None,
            "phases_completed": ["analyze", "classify", "verify", "evaluate"],
            "results_dir": str(run_dir.relative_to(_PROJECT_ROOT)),
            "metrics": metrics,
        }

    phases_completed: list[str] = []
    start = time.monotonic()

    def _fail(phase: str, error: str) -> dict:
        duration = round(time.monotonic() - start, 2)
        print(f"  [{app_name}] ✗ Phase '{phase}' failed: {error[:200]}")
        return {
            "application_name": app_name,
            "run_timestamp": run_timestamp,
            "status": "FAILED",
            "duration_seconds": duration,
            "error": f"{phase}: {error}",
            "phases_completed": phases_completed,
            "results_dir": str(run_dir.relative_to(_PROJECT_ROOT)),
            "metrics": None,
        }

    # ── Phase 1: analyze ──────────────────────────────────────────────
    print(f"\n  [{app_name}] Phase 1: analyze → {run_dir.name}/")
    rc, out = _run_cmd([
        sys.executable, "-m", "bola_sentinel.cli", "analyze", source_path,
        "--output", static_out,
    ], dry_run=dry_run)
    if rc != 0:
        return _fail("analyze", out[-500:])
    phases_completed.append("analyze")

    # ── Phase 2: classify ─────────────────────────────────────────────
    print(f"  [{app_name}] Phase 2: classify")
    rc, out = _run_cmd([
        sys.executable, "-m", "bola_sentinel.cli", "classify",
        "--input", static_out,
        "--output", llm_out,
    ], dry_run=dry_run)
    if rc != 0:
        return _fail("classify", out[-500:])
    phases_completed.append("classify")

    # ── Phase 3: verify ───────────────────────────────────────────────
    print(f"  [{app_name}] Phase 3: verify → {base_url}")
    rc, out = _run_cmd([
        sys.executable, "-m", "bola_sentinel.cli", "verify",
        "--target-url", base_url,
        "--input", llm_out,
        "--output", verify_out,
        "--test-users", test_users_file,     # ← per-app test_users, no file copying
    ], dry_run=dry_run)
    if rc != 0:
        return _fail("verify", out[-500:])
    phases_completed.append("verify")

    # ── Phase 4: evaluate ─────────────────────────────────────────────
    print(f"  [{app_name}] Phase 4: evaluate")
    rc, out = _run_cmd([
        sys.executable, "-m", "bola_sentinel.cli", "evaluate",
        "--app-name", app_name,
        "--input", verify_out,
        "--ground-truth", str(_PROJECT_ROOT / "datasets" / "ground_truth"),
        "--metrics-output", metrics_out,
        "--report-output", report_out,
    ], dry_run=dry_run)
    if rc != 0:
        return _fail("evaluate", out[-500:])
    phases_completed.append("evaluate")

    duration = round(time.monotonic() - start, 2)

    # Load metrics for aggregation.
    metrics: dict = {}
    if not dry_run and (run_dir / "evaluation_metrics.json").exists():
        metrics = json.loads((run_dir / "evaluation_metrics.json").read_text())

    print(f"  [{app_name}] ✓ Complete in {duration}s")
    return {
        "application_name": app_name,
        "run_timestamp": run_timestamp,
        "status": "SUCCESS",
        "duration_seconds": duration,
        "error": None,
        "phases_completed": phases_completed,
        "results_dir": str(run_dir.relative_to(_PROJECT_ROOT)),
        "metrics": metrics,
    }


# ── Full benchmark ─────────────────────────────────────────────────────────

def run_full_benchmark(
    app_filter: list[str] | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """
    Orchestrate the full benchmark across all registered applications.

    Steps
    -----
    1. Validate all ground-truth files — abort if errors found.
    2. Load app_registry.json.
    3. For each app (optionally filtered by --apps), call run_benchmark_for_app.
       Failures are recorded in the manifest but do NOT stop remaining apps.
    4. Aggregate: pool TP/FP/FN/TN across successful apps for each stage.
    5. Write results/benchmark_summary.json and results/benchmark_summary.md.
    6. Log full run to logs/evaluation_logs/benchmark_{timestamp}.json.
    """
    ts = _timestamp()
    print("=" * 68)
    print(f"  BOLA-Sentinel Benchmark Runner  [{ts}]")
    print("=" * 68)

    # ── Step 1: validate ground truth ─────────────────────────────────
    print("\n[1/6] Validating ground-truth files …")
    sys.path.insert(0, str(_PROJECT_ROOT))
    from datasets.validate_dataset import validate_all_ground_truth  # noqa: E402
    validation = validate_all_ground_truth()
    print(f"      {validation['total_entries']} entries, "
          f"{len(validation['errors'])} errors, "
          f"{len(validation['warnings'])} warnings")
    if not validation["passed"]:
        print("\n  ✗  Ground-truth validation FAILED.  Fix errors before benchmarking.")
        for e in validation["errors"]:
            idx = f"[{e['entry_index']}]" if e["entry_index"] is not None else ""
            print(f"     {e['file']}{idx}: {e['message']}")
        sys.exit(1)
    print("      ✓ Validation passed.")

    # ── Step 2: load registry ─────────────────────────────────────────
    print("\n[2/6] Loading app registry …")
    registry = _load_registry()
    if app_filter:
        registry = [e for e in registry if e["application_name"] in app_filter]
    print(f"      {len(registry)} application(s) to benchmark: "
          f"{[e['application_name'] for e in registry]}")

    if not registry:
        print("  No applications to run.  Check app_registry.json or --apps filter.")
        sys.exit(0)

    # ── Step 3: per-app runs ──────────────────────────────────────────
    print("\n[3/6] Running per-application pipelines …")
    manifest = _load_manifest()
    per_app_results: list[dict] = []
    failures: list[str] = []

    for app_entry in registry:
        app_name = app_entry["application_name"]
        result = run_benchmark_for_app(app_entry, ts, dry_run=dry_run, force=force)
        per_app_results.append(result)

        if result["status"] == "FAILED":
            failures.append(app_name)

        manifest = _upsert_manifest(manifest, {
            "application_name": app_name,
            "run_timestamp": ts,
            "status": result["status"],
            "duration_seconds": result["duration_seconds"],
            "error": result["error"],
            "phases_completed": result["phases_completed"],
            "results_dir": result["results_dir"],
            "git_commit": app_entry.get("git_commit", "UNKNOWN"),
            "dataset_version": app_entry.get("dataset_version", "UNKNOWN"),
            "llm_model": "qwen2.5:7b-instruct",
            "python_version": sys.version.split(" ")[0],
            "benchmark_config": {"dry_run": dry_run, "force": force}
        })
        _save_manifest(manifest)   # write after EVERY app for crash-safety

    # ── Step 4: pooled aggregation ────────────────────────────────────
    print("\n[4/6] Aggregating results …")
    successful = [
        r for r in per_app_results
        if r["status"] in ("SUCCESS", "SKIPPED") and r.get("metrics")
    ]
    app_metrics_list = [r["metrics"] for r in successful]

    stages = (
        "stage_1_static_only",
        "stage_2_static_plus_llm",
        "stage_3_final_system",
    )
    pooled: dict = {}
    for stage in stages:
        pooled[stage] = _pool_confusion_matrices(app_metrics_list, stage)

    fp1 = pooled["stage_1_static_only"]["fp"]
    fp2 = pooled["stage_2_static_plus_llm"]["fp"]
    fp3 = pooled["stage_3_final_system"]["fp"]
    pooled["fp_reduction_stage1_to_stage2"] = fp1 - fp2
    pooled["fp_reduction_stage2_to_stage3"] = fp2 - fp3
    pooled["fp_reduction_stage1_to_stage3_total"] = fp1 - fp3

    # ── Step 5: write outputs ─────────────────────────────────────────
    print("\n[5/6] Writing benchmark outputs …")
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "run_timestamp": ts,
        "applications_tested": [e["application_name"] for e in registry],
        "applications_successful": [r["application_name"] for r in successful],
        "applications_failed": failures,
        "per_application_results": {
            r["application_name"]: r["metrics"]
            for r in successful
        },
        "pooled_overall_results": pooled,
    }
    summary_json = _RESULTS_DIR / "benchmark_summary.json"
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"      → {summary_json.relative_to(_PROJECT_ROOT)}")

    summary_md = _RESULTS_DIR / "benchmark_summary.md"
    _write_markdown_summary(summary, summary_md)
    print(f"      → {summary_md.relative_to(_PROJECT_ROOT)}")

    # ── Step 6: evaluation log ────────────────────────────────────────
    print("\n[6/6] Writing evaluation log …")
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _LOG_DIR / f"benchmark_{ts}.json"
    log_record = {
        "run_timestamp": ts,
        "dry_run": dry_run,
        "force": force,
        "validation": validation,
        "per_app_run_results": per_app_results,
        "pooled_overall_results": pooled,
    }
    log_path.write_text(
        json.dumps(log_record, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"      → {log_path.relative_to(_PROJECT_ROOT)}")

    # ── Console summary ───────────────────────────────────────────────
    _print_console_summary(summary, failures, ts)


# ── Markdown summary writer ────────────────────────────────────────────────

def _fmt(v: float) -> str:
    return f"{v:.3f}"


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _stage_row(label: str, m: dict) -> str:
    return (
        f"| {label} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | "
        f"{_fmt(m['precision'])} | {_fmt(m['recall'])} | {_fmt(m['f1'])} | "
        f"{_pct(m['false_positive_rate'])} | {_pct(m['false_negative_rate'])} |"
    )


def _write_markdown_summary(summary: dict, out_path: Path) -> None:
    ts = summary["run_timestamp"]
    apps_ok = summary["applications_successful"]
    apps_fail = summary["applications_failed"]
    pooled = summary["pooled_overall_results"]
    per_app = summary["per_application_results"]

    lines = [
        "# BOLA-Sentinel Benchmark Summary",
        "",
        f"> Run timestamp: `{ts}`  ",
        f"> Applications tested: {len(summary['applications_tested'])}  ",
        f"> Successful: {len(apps_ok)}  |  Failed: {len(apps_fail)}",
        "",
    ]

    if apps_fail:
        lines += [
            "## ⚠ Failed Applications",
            "",
            "| Application | Note |",
            "|-------------|------|",
        ] + [f"| `{a}` | Pipeline failed — see run_manifest.json |" for a in apps_fail] + [""]

    # Per-application tables.
    if per_app:
        lines += [
            "## Per-Application Results",
            "",
        ]
        for app_name, metrics in per_app.items():
            if not metrics:
                continue
            lines += [
                f"### {app_name}",
                "",
                "| Stage | TP | FP | FN | TN | Precision | Recall | F1 | FPR | FNR |",
                "|-------|----|----|----|----|-----------|--------|-----|-----|-----|",
                _stage_row("Stage 1 — Static Only",      metrics.get("stage_1_static_only", {})),
                _stage_row("Stage 2 — Static + LLM",     metrics.get("stage_2_static_plus_llm", {})),
                _stage_row("Stage 3 — Full Pipeline",    metrics.get("stage_3_final_system", {})),
                "",
            ]

    # Multi-Dataset Comparison table
    if per_app:
        lines += [
            "## Multi-Dataset Comparison",
            "",
            "| Application | Coverage | Precision | Recall | F1 | FPR | Accuracy |",
            "|-------------|----------|-----------|--------|----|-----|----------|",
        ]
        for app_name, metrics in per_app.items():
            if not metrics:
                continue
            stage3 = metrics.get("stage_3_final_system", {})
            cov = _pct(metrics.get("coverage", 0.0))
            prec = _fmt(stage3.get("precision", 0.0))
            rec = _fmt(stage3.get("recall", 0.0))
            f1 = _fmt(stage3.get("f1", 0.0))
            fpr = _pct(stage3.get("false_positive_rate", 0.0))
            acc = _fmt(stage3.get("accuracy", 0.0))
            lines.append(f"| {app_name} | {cov} | {prec} | {rec} | {f1} | {fpr} | {acc} |")
        lines.append("")

    # Pooled table.
    lines += [
        "## Pooled Overall Results",
        "",
        "> TP/FP/FN/TN are **summed** across all applications before computing",
        "> metrics — not averaged — to avoid statistical distortion from apps",
        "> with different route counts.",
        "",
        "| Stage | TP | FP | FN | TN | Precision | Recall | F1 | FPR | FNR |",
        "|-------|----|----|----|----|-----------|--------|-----|-----|-----|",
        _stage_row("**Stage 1** — Static Only",   pooled.get("stage_1_static_only", {})),
        _stage_row("**Stage 2** — Static + LLM",  pooled.get("stage_2_static_plus_llm", {})),
        _stage_row("**Stage 3** — Full Pipeline", pooled.get("stage_3_final_system", {})),
        "",
    ]

    # FP reduction section.
    fp1 = pooled.get("stage_1_static_only", {}).get("fp", 0)
    fp2 = pooled.get("stage_2_static_plus_llm", {}).get("fp", 0)
    fp3 = pooled.get("stage_3_final_system", {}).get("fp", 0)
    d12 = pooled.get("fp_reduction_stage1_to_stage2", fp1 - fp2)
    d23 = pooled.get("fp_reduction_stage2_to_stage3", fp2 - fp3)
    d13 = pooled.get("fp_reduction_stage1_to_stage3_total", fp1 - fp3)

    lines += [
        "## False-Positive Reduction — Primary Research Claim",
        "",
        "| Transition | FP Before | FP After | Reduction |",
        "|------------|-----------|----------|-----------|",
        f"| Stage 1 → Stage 2 (adding LLM reasoning) | {fp1} | {fp2} | **{d12}** fewer FPs |",
        f"| Stage 2 → Stage 3 (adding dynamic verification) | {fp2} | {fp3} | **{d23}** fewer FPs |",
        f"| Stage 1 → Stage 3 **(total)** | {fp1} | {fp3} | **{d13}** fewer FPs |",
        "",
        f"Adding LLM reasoning and then dynamic verification reduced false positives by a "
        f"total of **{d13}** across the full benchmark "
        f"(from {fp1} in static-only to {fp3} in the full pipeline).",
        "",
        "## Reproducibility",
        "",
        "Every run is fully logged:",
        "- `results/benchmark_runs/<app>/`  — per-app phase outputs",
        "- `results/benchmark_runs/run_manifest.json`  — run manifest with status + duration",
        f"- `logs/evaluation_logs/benchmark_{ts}.json`  — full aggregated log",
        "",
    ]

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Console output ─────────────────────────────────────────────────────────

def _print_console_summary(summary: dict, failures: list[str], ts: str) -> None:
    pooled = summary["pooled_overall_results"]
    s1 = pooled.get("stage_1_static_only", {})
    s2 = pooled.get("stage_2_static_plus_llm", {})
    s3 = pooled.get("stage_3_final_system", {})

    def _row(label: str, m: dict) -> str:
        return (
            f"  {label:36s}  "
            f"P={m.get('precision', 0):.3f}  R={m.get('recall', 0):.3f}  "
            f"F1={m.get('f1', 0):.3f}  "
            f"FPR={m.get('false_positive_rate', 0) * 100:.1f}%  "
            f"FP={m.get('fp', 0)}  TP={m.get('tp', 0)}"
        )

    d12 = pooled.get("fp_reduction_stage1_to_stage2", 0)
    d23 = pooled.get("fp_reduction_stage2_to_stage3", 0)
    d13 = pooled.get("fp_reduction_stage1_to_stage3_total", 0)

    print(f"\n{'═' * 68}")
    print(f"  Benchmark Complete  [{ts}]")
    print(f"{'═' * 68}")
    print(f"  Apps tested:    {len(summary['applications_tested'])}")
    print(f"  Successful:     {len(summary['applications_successful'])}")
    print(f"  Failed:         {len(failures)} {failures if failures else ''}")
    print(f"{'─' * 68}")
    print(f"  POOLED METRICS (summed TP/FP/FN/TN across all apps):")
    print(_row("Stage 1  Static Only", s1))
    print(_row("Stage 2  Static + LLM", s2))
    print(_row("Stage 3  Full Pipeline (Final)", s3))
    print(f"{'─' * 68}")
    print(f"  False-Positive Reduction:")
    print(f"    Stage 1 → 2 (adding LLM):               {d12:+d} FPs")
    print(f"    Stage 2 → 3 (adding dynamic verif.):    {d23:+d} FPs")
    print(f"    Stage 1 → 3 total:                      {d13:+d} FPs")
    print(f"{'─' * 68}")
    print(f"  Outputs:")
    print(f"    results/benchmark_summary.json")
    print(f"    results/benchmark_summary.md")
    print(f"    results/benchmark_runs/run_manifest.json")
    print(f"    logs/evaluation_logs/benchmark_{ts}.json")
    print(f"{'═' * 68}\n")


# ── CLI ────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_benchmark.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--apps", nargs="+", metavar="APP_NAME",
        help="Run only these application(s) from app_registry.json.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run even if results already exist (disables resumption).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print subprocess commands without executing them.",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    run_full_benchmark(
        app_filter=args.apps,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
